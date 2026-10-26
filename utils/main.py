import json
import re
import unicodedata
from prompt.detector_grocerias import procesar_pregunta
from prompt.principal import construir_prompt
from utils.milvus.busqueda import search
from utils.milvus.indexar import indexar
from utils.gpt.gptapi import generar_respuesta
from utils.personalizacion import elegir_apertura
from utils.config import (
    COL_CONOCIMIENTO,
    COL_INTERACCIONES,
    MOVIMIENTOS_PATH,
    UMBRAL_CONOCIMIENTO,
    UMBRAL_INTERACCIONES,
)



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


MOVIMIENTO_POR_DEFECTO = 1

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


# Etiquetas que significan "no hay nombre": nunca se dicen ni se guardan.
_ETIQUETAS_SIN_NOMBRE = {"", "persona no identificada", "(sin nombre)", "sin nombre"}
_FRASE_SIN_NOMBRE = r"(?:persona\s+no\s+identificada|\(sin\s+nombre\))"


def _etiqueta_real(etiqueta) -> str:
    """Devuelve la etiqueta si es un nombre real; si no, cadena vacía."""
    etiqueta = (etiqueta or "").strip()
    return "" if etiqueta.lower() in _ETIQUETAS_SIN_NOMBRE else etiqueta


def _limpiar_sin_nombre(texto: str) -> str:
    """Quita de un texto las frases 'Persona no identificada' / '(sin nombre)'."""
    texto = re.sub(rf"^\s*{_FRASE_SIN_NOMBRE}\s*[,:;]\s*", "", texto, flags=re.IGNORECASE)
    texto = re.sub(rf"\s*,\s*{_FRASE_SIN_NOMBRE}", "", texto, flags=re.IGNORECASE)
    texto = texto.strip()
    return texto[0].upper() + texto[1:] if texto else texto


# Palabras iniciales que son nombres propios: conservan la mayúscula tras "Nombre, ".
_NOMBRES_PROPIOS = {"universidad", "prometeo", "colombia", "bogotá", "bogota", "libre"}


def _anteponer_nombre(etiqueta: str, respuesta: str, apertura: str | None = None) -> str:
    """
    Personaliza una respuesta de caché SIN modificar su contenido.

    - nombre + apertura: "Pedro, veo que buscas orientación. El sol se ve…"
    - solo apertura:     "Veo que buscas orientación. El sol se ve…"
    - solo nombre:       "Pedro, el sol se ve…" (ajusta la mayúscula inicial; no toca
                         siglas ni nombres propios como R-One, UNAL o Prometeo)
    - ninguno:           la respuesta tal cual.
    """
    if apertura:
        apertura = apertura.strip().rstrip(".,;:!?")
        if etiqueta:
            return f"{etiqueta}, {apertura}. {respuesta}"
        return f"{apertura[0].upper()}{apertura[1:]}. {respuesta}"
    if not etiqueta:
        return respuesta
    primera = respuesta.split(maxsplit=1)[0] if respuesta.strip() else ""
    palabra = re.sub(r"[^\wáéíóúüñÁÉÍÓÚÜÑ-]", "", primera)
    es_normal = (
        primera[:1].isalpha()
        and primera[:1].isupper()
        and palabra[1:] == palabra[1:].lower()      # sin otras mayúsculas (UNAL, R-One)
        and "-" not in palabra
        and palabra.lower() not in _NOMBRES_PROPIOS
    )
    if es_normal:
        respuesta = respuesta[0].lower() + respuesta[1:]
    return f"{etiqueta}, {respuesta}"


def _terminos_nombre(etiqueta: str) -> list[str]:
    """Etiqueta completa y cada palabra suya (>=3 letras), de mayor a menor longitud."""
    etiqueta = _etiqueta_real(etiqueta)
    if not etiqueta:
        return []
    terminos = {etiqueta} | {p for p in etiqueta.split() if len(p) >= 3}
    return sorted(terminos, key=len, reverse=True)


def _quitar_nombre(respuesta: str, etiqueta: str) -> str | None:
    """
    Elimina el nombre de la persona de la respuesta antes de guardarla en Milvus.
    Devuelve None si el nombre sigue apareciendo (no se debe indexar).
    """
    texto = _limpiar_sin_nombre(respuesta)
    for t in _terminos_nombre(etiqueta):
        nombre = re.escape(t)
        # "Andrea, ..." al inicio de la respuesta
        texto = re.sub(rf"^\s*{nombre}\s*[,:;]\s*", "", texto, flags=re.IGNORECASE)
        # "¡Hola, Andrea!" / "gracias, Andrea." / "..., Andrea, ..."
        texto = re.sub(rf"\s*,\s*{nombre}\b", "", texto, flags=re.IGNORECASE)

    texto = texto.strip()
    if texto:
        texto = texto[0].upper() + texto[1:]

    if re.search(_FRASE_SIN_NOMBRE, texto, flags=re.IGNORECASE):
        return None
    for t in _terminos_nombre(etiqueta):
        if re.search(rf"\b{re.escape(t)}\b", texto, flags=re.IGNORECASE):
            return None
    return texto or None


def _respuesta_interaccion_almacenable(respuesta) -> bool:
    if not isinstance(respuesta, str):
        return False
    respuesta_norm = " ".join(respuesta.lower().split())
    if not respuesta_norm or respuesta_norm in _RESPUESTAS_GENERICAS:
        return False
    return not any(marca in respuesta_norm for marca in _RESPUESTAS_NO_ALMACENABLES)


def _normalizar_movimiento(movimientos) -> int:
    if isinstance(movimientos, str):
        try:
            movimientos = json.loads(movimientos)
        except json.JSONDecodeError:
            return MOVIMIENTO_POR_DEFECTO

    if isinstance(movimientos, list) and movimientos:
        try:
            return int(movimientos[0])
        except (TypeError, ValueError):
            pass

    if isinstance(movimientos, int):
        return movimientos

    return MOVIMIENTO_POR_DEFECTO


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

    cache = search(COL_CONOCIMIENTO, pregunta_limpia, umbral_conocimiento)

    if not cache["hit"]:
        # Las interacciones generadas se consultan solo con coincidencia exacta.
        cache = search(
            COL_INTERACCIONES,
            pregunta_limpia,
            UMBRAL_INTERACCIONES,
            solo_exacto=True,
        )

    # Solo hay etiqueta si es un nombre real; "Persona no identificada" = sin nombre.
    etiqueta = _etiqueta_real(getattr(obj, "etiqueta", None))

    # ── Ruta caché ────────────────────────────────────────────────────────────
    # La respuesta cacheada no pasa por el LLM, así que el nombre se incorpora
    # aquí manualmente (solo si existe) antes de devolver el resultado.
    if cache["hit"]:
        respuesta_raw = _limpiar_sin_nombre(str(cache["data"]["respuesta"]))
        # Apertura según el contexto visual (embeddings locales, sin LLM).
        apertura = elegir_apertura(getattr(obj, "contexto", None))
        return {
            "respuesta": _anteponer_nombre(etiqueta, respuesta_raw, apertura),
            "movimiento": _normalizar_movimiento(cache["data"]["movimientos"]),
            "fuente": "cache",
            "etiqueta": etiqueta,
        }

    # ── Ruta LLM ──────────────────────────────────────────────────────────────
    # construir_prompt ya inyecta etiqueta y contexto en el prompt; el modelo
    # devuelve una respuesta ya personalizada, no hace falta prefijo manual.
    prompt = construir_prompt(obj, pregunta_limpia, secuencias)
    salida = generar_respuesta(prompt)
    salida["respuesta"] = _limpiar_sin_nombre(str(salida["respuesta"]))

    # Indexar la interacción si no tenía groserías y la respuesta es almacenable.
    # El nombre de la persona NO se guarda en la base vectorial: se elimina de la
    # respuesta antes de indexar (si no se puede quitar limpiamente, no se indexa).
    if (
        not tenia_groseria
        and _respuesta_interaccion_almacenable(salida.get("respuesta"))
    ):
        respuesta_sin_nombre = _quitar_nombre(salida["respuesta"], etiqueta)
        if respuesta_sin_nombre:
            indexar(
                pregunta_limpia,
                respuesta_sin_nombre,
                salida["movimientos"],
                collection_name=COL_INTERACCIONES,
            )

    return {
        "respuesta": salida["respuesta"],
        "movimiento": _normalizar_movimiento(salida["movimientos"]),
        "fuente": "llm",
        "backend": salida.get("_backend", "gguf"),
        "etiqueta": etiqueta,
    }
