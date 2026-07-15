import re
import unicodedata

from utils.milvus.conexion import get_client
from utils.encoder.encoder import embed          
from utils.config import SEARCH_PARAMS


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^\w\s]", " ", texto)
    return " ".join(texto.split())


def search(coleccion: str, texto: str, umbral: float) -> dict:
    client = get_client()
    vector = embed(texto)  
    texto_norm = _normalizar(texto)

    if not client.has_collection(collection_name=coleccion):
        return {"hit": False, "score": 0, "data": None}

    try:
        client.load_collection(collection_name=coleccion)
    except Exception:
        return {"hit": False, "score": 0, "data": None}

    # Paso rápido: buscar coincidencias textuales simples en la colección.
    try:
        registros = client.query(
            collection_name=coleccion,
            filter="",
            output_fields=["pregunta", "respuesta", "movimientos"],
            limit=1000,
        )

        mejores_palabras = 0.0
        mejor_registro = None

        palabras_texto = set(texto_norm.split())
        for reg in registros or []:
            pregunta_reg = _normalizar(reg.get("pregunta", ""))
            if not pregunta_reg:
                continue

            if texto_norm == pregunta_reg or texto_norm in pregunta_reg or pregunta_reg in texto_norm:
                return {"hit": True, "score": 1.0, "data": reg}

            palabras_reg = set(pregunta_reg.split())
            if not palabras_texto or not palabras_reg:
                continue

            interseccion = len(palabras_texto & palabras_reg)
            union = len(palabras_texto | palabras_reg)
            score_textual = interseccion / union if union else 0.0

            if score_textual > mejores_palabras:
                mejores_palabras = score_textual
                mejor_registro = reg

        if mejor_registro is not None and mejores_palabras >= 0.45:
            return {"hit": True, "score": mejores_palabras, "data": mejor_registro}
    except Exception:
        pass

    try:
        resultados = client.search(
            collection_name=coleccion,
            data=[vector],
            limit=1,
            output_fields=["pregunta", "respuesta", "movimientos"],
            search_params=SEARCH_PARAMS,
        )
    except Exception:
        return {"hit": False, "score": 0, "data": None}

    if not resultados or not resultados[0]:
        return {"hit": False, "score": 0, "data": None}

    mejor = resultados[0][0]
    score = mejor["distance"]      

    #esto toca adecuarlo ya a nuestra arq de  gpt, pero por ahora lo dejamos así para probar la búsqueda vectorial
    if score >= umbral:
        return {"hit": True, "score": score, "data": mejor["entity"]}    
    return {"hit": False, "score": score, "data": None}


