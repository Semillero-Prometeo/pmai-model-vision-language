
import json
from utils.milvus.conexion import get_client
from utils.encoder.encoder import embed
from utils.config import COL_CONOCIMIENTO


def indexar(pregunta: str, respuesta: str, movimientos: list = None) -> None:

    if movimientos is None:
        movimientos = []

    client = get_client()

    data = [{
        "pregunta":    pregunta,
        "respuesta":   respuesta,
        "movimientos": json.dumps(movimientos),  
        "vector":      embed(pregunta),          
    }]

    client.insert(collection_name=COL_CONOCIMIENTO, data=data)