from utils.config import MILVUS_DB_PATH
from pymilvus import MilvusClient



#acceso a milvus conexion
# sirve para obtener el cliente de milvus y poder hacer consultas a la base de datos
# ademas nos da la posibilidad de cambiar la conexion a milvus en un solo lugar si es necesario
_client = MilvusClient(MILVUS_DB_PATH)

# funcion para obtener el cliente de milvus
def get_client() -> MilvusClient:
    return _client