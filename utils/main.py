import json
from prompt.detector_grocerias import procesar_pregunta
from prompt.principal import construir_prompt
from utils.milvus.busqueda import search
from utils.milvus.indexar import indexar
from utils.gpt.gptapi import generar_respuesta
from utils.config import COL_CONOCIMIENTO, COL_INTERACCIONES, UMBRAL_CONOCIMIENTO, UMBRAL_INTERACCIONES



#pipeline de procesamiento de preguntas y respuestas aca ya juntamos todito todito 


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
# aca procesamos si la pregunta tenia groserias o no, si tenia groserias no se indexa en la base de datos
    tenia_groseria = proc["tenia_groseria"]
#aca es donde se procesa la pregunta y se genera la respuesta, primero se busca en la cache,
#  si no hay cache se genera la respuesta con el modelo de
#  lenguaje y finalmente se indexa la pregunta y respuesta en la base de datos
    cache = search(COL_CONOCIMIENTO, pregunta_limpia, UMBRAL_CONOCIMIENTO)

#aca es donde se procesa la pregunta y se genera la respuesta, primero se busca en la cache,
#  si no hay cache se genera la respuesta con el modelo de lenguaje y finalmente se indexa la pregunta y respuesta en la base de datos
    if not cache["hit"]:
        cache = search(COL_INTERACCIONES, pregunta_limpia, UMBRAL_INTERACCIONES)

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
        indexar(pregunta_limpia, salida["respuesta"], salida["movimientos"])


# aca se retorna la respuesta y los movimientos que se deben realizar para responder a la pregunta, junto con la fuente de la respuesta (cache o llm)
    return {
        "respuesta": salida["respuesta"],
        "movimientos": salida["movimientos"],
        "fuente": "llm",
    }