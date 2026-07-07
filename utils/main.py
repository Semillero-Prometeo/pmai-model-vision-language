import json
from prompt.detector_grocerias import procesar_pregunta
from prompt.principal import construir_prompt
from utils.milvus.busqueda import search
from utils.milvus.indexar import indexar
from utils.gpt.gptapi import generar_respuesta
from utils.config import COL_CONOCIMIENTO, UMBRAL_CONOCIMIENTO


def cargar_movimientos(path="data/movimientos.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def responder(obj, secuencias):
    pregunta = getattr(obj, "question", None) or ""
    proc = procesar_pregunta(pregunta)
    pregunta_limpia = proc["pregunta_limpia"]
    tenia_groseria = proc["tenia_groseria"]
    cache = search(COL_CONOCIMIENTO, pregunta_limpia, UMBRAL_CONOCIMIENTO)


    if cache["hit"]:
        return {
            "respuesta": cache["data"]["respuesta"],
            "movimientos": cache["data"]["movimientos"],
            "fuente": "cache",
        }


    prompt = construir_prompt(obj, pregunta_limpia, secuencias)
    salida = generar_respuesta(prompt)



    if not tenia_groseria:
        indexar(pregunta_limpia, salida["respuesta"], salida["movimientos"])

    return {
        "respuesta": salida["respuesta"],
        "movimientos": salida["movimientos"],
        "fuente": "llm",
    }