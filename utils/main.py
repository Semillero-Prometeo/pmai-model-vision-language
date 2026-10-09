import json
import logging
import re
import unicodedata
from prompt.detector_grocerias import procesar_pregunta
from prompt.principal import construir_prompt
from utils.milvus.busqueda import search
from utils.milvus.indexar import indexar
from utils.gpt.gptapi import generar_respuesta
from utils.config import (
    COL_CONOCIMIENTO,
    COL_INTERACCIONES,
    MOVIMIENTOS_PATH,
    UMBRAL_CONOCIMIENTO,
    UMBRAL_INTERACCIONES,
)

logger = logging.getLogger(__name__)


#pipeline de procesamiento de preguntas y respuestas aca ya juntamos todito todito 


INTENCIONES_SOCIALES = (
    "saludo_social",
    "identidad_universidad",
)


def _normalizar_texto(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[¿?¡!.,;:\-_/()\[\]{}\"'`]+", " ", texto)
    return " ".join(texto.split())


#esto es una recomendacion por que hay problemas para identificar intenciones

def _contiene_termino(texto: str, terminos: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(termino)}\b", texto) for termino in terminos)


def detectar_intencion(pregunta: str) -> str:
    """Clasifica la intención principal de una pregunta normalizada."""
    pregunta_norm = _normalizar_texto(pregunta or "")

    if not pregunta_norm:
        return "general"

    # Solo clasifica como saludo cuando no contiene otra consulta.
    saludos = ("hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey")
    if _contiene_termino(pregunta_norm, saludos) and len(pregunta_norm.split()) <= 4:
        return "saludo_social"

    identidad = (
        "quien eres", "como te llamas", "que eres", "r one", "universidad libre",
        "prometeo", "tu nombre", "tu proposito",
    )
    if any(termino in pregunta_norm for termino in identidad):
        return "identidad_universidad"

    beneficios = (
        "beneficio", "beneficios", "ventaja", "ventajas", "opinion", "recomiendas",
        "conviene", "vale la pena", "por que", "porque",
    )
    if any(termino in pregunta_norm for termino in beneficios):
        return "beneficio_opinion"

    datos = (
        "cuanto", "cuantos", "cuanta", "cuantas", "donde", "cual", "cuales",
        "quien", "cuando", "horario", "sede", "departamento", "facultad",
        "requisito", "requisitos", "precio", "direccion", "telefono", "correo",
        "fecha", "fechas", "nombre",
    )
    if _contiene_termino(pregunta_norm, datos):
        return "dato_especifico"

    return "general"


_RESPUESTAS_NO_ALMACENABLES = (
    "no dispongo de ese dato",
    "no tengo información suficiente",
    "no tengo informacion suficiente",
    "prefiero no darte una cifra inexacta",
)
_RESPUESTAS_GENERICAS = {
    "claro, puedo ayudarte",
    "con gusto te ayudo",
    "no lo sé",
    "no lo se",
}


def _respuesta_interaccion_almacenable(respuesta) -> bool:
    if not isinstance(respuesta, str):
        return False
    respuesta_norm = " ".join(respuesta.lower().split())
    if not respuesta_norm or respuesta_norm in _RESPUESTAS_GENERICAS:
        return False
    return not any(marca in respuesta_norm for marca in _RESPUESTAS_NO_ALMACENABLES)


def _movimientos_de_salida(movimientos, permitidos: set[int]) -> list[int]:
    from utils.gguf.ggufapi import _validar_movimientos

    if isinstance(movimientos, str):
        try:
            movimientos = json.loads(movimientos)
        except json.JSONDecodeError:
            return []
    return _validar_movimientos(movimientos, permitidos)[:3]


# cargamos los movimientos desde un archivo JSON el que ha hicimos
def cargar_movimientos(path=None):
    movimientos_path = MOVIMIENTOS_PATH if path is None else path
    with open(movimientos_path, "r", encoding="utf-8") as f:
        return json.load(f)


# aca es donde se procesa la pregunta y se genera la respuesta,
# primero se limpia la pregunta, luego se busca en la cache,
# si no hay cache se genera la respuesta con el modelo de lenguaje y
# finalmente se indexa la pregunta y respuesta en la base de datos
def responder(obj, secuencias):
    pregunta = getattr(obj, "question", None) or ""
    proc = procesar_pregunta(pregunta)
    pregunta_limpia = proc["pregunta_limpia"]
    intencion = detectar_intencion(pregunta_limpia)
    # aca procesamos si la pregunta tenia groserias o no, si tenia groserias no se indexa en la base de datos
    tenia_groseria = proc["tenia_groseria"]

    # Primero se consulta conocimiento y, si no hay hit, interacciones.
    # Conocimiento tiene prioridad y ambas colecciones se mantienen separadas.
    umbral_conocimiento = UMBRAL_CONOCIMIENTO
    if intencion == "dato_especifico":
        umbral_conocimiento = min(UMBRAL_CONOCIMIENTO, 0.28)

    permitidos = {int(item["id"]) for item in secuencias}
    milvus_caido = False

    try:
        cache = search(COL_CONOCIMIENTO, pregunta_limpia, umbral_conocimiento)
    except Exception:
        milvus_caido = True
        cache = {"hit": False}

    if not cache["hit"]:
        # Las interacciones generadas se consultan solo con coincidencia exacta.
        try:
            cache = search(
                COL_INTERACCIONES,
                pregunta_limpia,
                UMBRAL_INTERACCIONES,
                solo_exacto=True,
            )
        except Exception:
            milvus_caido = True
            cache = {"hit": False}

    etiqueta = getattr(obj, "etiqueta", None) or "Persona no identificada"

    # ── Ruta caché ────────────────────────────────────────────────────────────
    # La respuesta cacheada no pasa por el LLM, así que el contexto visual y la
    # etiqueta se incorporan aquí manualmente antes de devolver el resultado.
    if cache["hit"]:
        respuesta_raw = str(cache["data"]["respuesta"])
        return {
            "respuesta": f"{etiqueta}, {respuesta_raw}",
            "movimientos": _movimientos_de_salida(
                cache["data"].get("movimientos"), permitidos
            ),
            "fuente": "cache",
            "etiqueta": etiqueta,
        }

    # ── Ruta LLM ──────────────────────────────────────────────────────────────
    # construir_prompt ya inyecta etiqueta y contexto en el prompt; el modelo
    # devuelve una respuesta ya personalizada, no hace falta prefijo manual.
    prompt = construir_prompt(obj, pregunta_limpia, secuencias)
    salida = generar_respuesta(prompt)

    # Indexar la interacción si no tenía groserías y la respuesta es almacenable.
    if (
        not milvus_caido
        and not tenia_groseria
        and _respuesta_interaccion_almacenable(salida.get("respuesta"))
    ):
        try:
            indexar(
                pregunta_limpia,
                salida["respuesta"],
                salida["movimientos"],
                collection_name=COL_INTERACCIONES,
            )
        except Exception:
            logger.exception("No se pudo indexar la interacción en Milvus")

    return {
        "respuesta": salida["respuesta"],
        "movimientos": _movimientos_de_salida(salida.get("movimientos"), permitidos),
        "fuente": "llm",
        "backend": salida.get("_backend", "gguf"),
        "etiqueta": etiqueta,
    }
