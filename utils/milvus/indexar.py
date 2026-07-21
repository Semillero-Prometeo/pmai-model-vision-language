

import json
from utils.milvus.conexion import get_client
from utils.encoder.encoder import embed
from utils.config import COL_CONOCIMIENTO

# esta función indexa una pregunta, respuesta y movimientos en la colección de conocimiento de Milvus.
# toca hacer  una para la base de interacciones también, pero esa la hacemos después :(

def indexar(pregunta: str, respuesta: str, movimientos: list = None) -> None:

# aca hacemos un checkeo de que movimientos no sea None, si lo es lo inicializamos como una lista vacía
    if movimientos is None:
        movimientos = []


# aca hacemos un checkeo de que la pregunta y la respuesta no sean None, si lo son los inicializamos como strings vacíos
    client = get_client()

    data = [{
        "pregunta":    pregunta,
        "respuesta":   respuesta,
        "movimientos": json.dumps(movimientos),  
        "vector":      embed(pregunta),          
    }]
    client.insert(collection_name=COL_CONOCIMIENTO, data=data)