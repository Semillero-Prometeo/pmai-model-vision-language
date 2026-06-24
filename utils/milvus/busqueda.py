from utils.milvus.conexion import get_client
from utils.encoder.encoder import embed          
from utils.config import SEARCH_PARAMS


def search(coleccion: str, texto: str, umbral: float) -> dict:
    client = get_client()
    vector = embed(texto)  

    resultados = client.search(
        collection_name=coleccion,
        data=[vector],
        limit=1,                                       
        output_fields=["pregunta", "respuesta", "movimientos"],
        search_params=SEARCH_PARAMS,
    )

    mejor = resultados[0][0]
    score = mejor["distance"]      

    #esto toca adecuarlo ya a nuestra arq de  gpt, pero por ahora lo dejamos así para probar la búsqueda vectorial
    if score >= umbral:
        return {"hit": True, "score": score, "data": mejor["entity"]}    
    return {"hit": False, "score": score, "data": None}


