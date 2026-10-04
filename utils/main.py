import json
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
# aca es donde se procesa la pregunta y se genera la respuesta,
    pregunta = getattr(obj, "question", None) or ""
    proc = procesar_pregunta(pregunta)
#aca es donde se procesa la pregunta y se genera la respuesta,
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

    # Si ninguna colección contiene una respuesta, se consulta el modelo.
    if cache["hit"]:
        return {
            "respuesta": str(cache["data"]["respuesta"]),
            "movimiento": _normalizar_movimiento(cache["data"]["movimientos"]),
            "fuente": "cache",
        }

# aca el prompt se construye con la pregunta limpia y las secuencias, luego se genera la respuesta con el modelo de lenguaje
# de esta manera se obtiene la respuesta y los movimientos que se deben realizar para responder a la pregunta
# al no encontrarla en el cache
    prompt = construir_prompt(obj, pregunta_limpia, secuencias)
    salida = generar_respuesta(prompt)


# aca se indexa la pregunta y respuesta en la base de datos, si no tenia groserias, para que pueda ser utilizada en futuras consultas
    if (
        not tenia_groseria
        and _respuesta_interaccion_almacenable(salida.get("respuesta"))
    ):
        indexar(
            pregunta_limpia,
            salida["respuesta"],
            salida["movimientos"],
            collection_name=COL_INTERACCIONES,
        )


# aca se retorna la respuesta y los movimientos que se deben realizar para responder a la pregunta, junto con la fuente de la respuesta (cache o llm)
    return {
        "respuesta": str(salida["respuesta"]),
        "movimiento": _normalizar_movimiento(salida["movimientos"]),
        "fuente": "llm",
    }