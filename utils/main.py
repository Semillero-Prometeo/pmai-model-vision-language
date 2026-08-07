import json
import re
from prompt.detector_grocerias import procesar_pregunta
from prompt.principal import construir_prompt
from utils.milvus.busqueda import search
from utils.milvus.indexar import indexar
from utils.gpt.gptapi import generar_respuesta
from utils.config import COL_CONOCIMIENTO, COL_INTERACCIONES, UMBRAL_CONOCIMIENTO, UMBRAL_INTERACCIONES



#pipeline de procesamiento de preguntas y respuestas aca ya juntamos todito todito 


INTENCIONES_SOCIALES = (
    "saludo_social",
    "identidad_universidad",
)


def _normalizar_texto(texto: str) -> str:
    texto = texto.lower()
    texto = re.sub(r"[¿?¡!.,;:\-_/()\[\]{}\"'`]+", " ", texto)
    return " ".join(texto.split())


#esto es una recomendacion por que hay problemas para identificar intenciones

def detectar_intencion(pregunta: str) -> str:
    """
    Clasifica la intención principal de la pregunta con reglas simples.

    Intenciones soportadas:
    - saludo_social
    - identidad_universidad
    - beneficio_opinion
    - dato_especifico
    - general
    """
    pregunta_norm = _normalizar_texto(pregunta or "")

    if not pregunta_norm:
        return "general"

    if re.search(r"\b(hola|buenas|buenos dias|buenas tardes|buenas noches|que tal|cómo estás|como estás)\b", pregunta_norm):
        return "saludo_social"

    if re.search(r"\b(quien eres|cómo te llamas|como te llamas|qué eres|que eres|r[- ]?one|universidad libre|prometeo)\b", pregunta_norm):
        return "identidad_universidad"

    if re.search(r"\b(beneficio|beneficios|ventaja|ventajas|opinion|opinión|recomiendas|conviene|vale la pena|por qué|porque)\b", pregunta_norm):
        return "beneficio_opinion"

    if re.search(r"\b(cuanto|cuantos|cuanta|cuantas|dónde|donde|cuál|cual|cuáles|cuales|quién|quien|cuándo|cuando|horario|sede|departamento|facultad|requisito|requisitos|precio|dirección|direccion|teléfono|telefono|correo|fecha|fechas)\b", pregunta_norm):
        return "dato_especifico"

    return "general"


# cargamos los movimientos desde un archivo JSON el que ha hicimos 
def cargar_movimientos(path="data/movimientos.json"):
    with open(path, "r", encoding="utf-8") as f:
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

# primero se decide si vale la pena usar caché según la intención
    cache = {"hit": False, "score": 0.0, "data": None}

    if intencion in ("identidad_universidad", "dato_especifico"):
        # caché de conocimiento: solo para preguntas informativas que suelen repetirse
        umbral_conocimiento = UMBRAL_CONOCIMIENTO
        if intencion == "dato_especifico":
            umbral_conocimiento = min(UMBRAL_CONOCIMIENTO, 0.28)

        cache = search(COL_CONOCIMIENTO, pregunta_limpia, umbral_conocimiento)

    if not cache["hit"] and intencion in ("saludo_social", "identidad_universidad", "dato_especifico"):
        # caché de interacciones: solo exacta o casi exacta
        cache = search(
            COL_INTERACCIONES,
            pregunta_limpia,
            UMBRAL_INTERACCIONES,
            solo_exacto=True,
        )

    # Para opinión/beneficios, saltamos el caché semántico y vamos directo al modelo
    if not cache["hit"] and intencion == "beneficio_opinion":
        cache = search(
            COL_INTERACCIONES,
            pregunta_limpia,
            UMBRAL_INTERACCIONES,
            solo_exacto=True,
        )

#aca es donde se procesa la pregunta y se genera la respuesta, primero se busca en la cache,
#  si no hay cache se genera la respuesta con el modelo de lenguaje y finalmente se index
# a la pregunta y respuesta en la base de datos
    if cache["hit"]:
        return {
            "respuesta": cache["data"]["respuesta"],
            "movimientos": cache["data"]["movimientos"],
            "fuente": "cache",
        }

# aca el prompt se construye con la pregunta limpia y las secuencias, luego se genera la respuesta con el modelo de lenguaje
# de esta manera se obtiene la respuesta y los movimientos que se deben realizar para responder a la pregunta
# al no encontrarla en el cache
    prompt = construir_prompt(obj, pregunta_limpia, secuencias)
    salida = generar_respuesta(prompt)


# aca se indexa la pregunta y respuesta en la base de datos, si no tenia groserias, para que pueda ser utilizada en futuras consultas
    if not tenia_groseria:
        indexar(
            pregunta_limpia,
            salida["respuesta"],
            salida["movimientos"],
            collection_name=COL_INTERACCIONES,
        )


# aca se retorna la respuesta y los movimientos que se deben realizar para responder a la pregunta, junto con la fuente de la respuesta (cache o llm)
    return {
        "respuesta": salida["respuesta"],
        "movimientos": salida["movimientos"],
        "fuente": "llm",
    }