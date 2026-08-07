from utils.config import MILVUS_DB_PATH, COL_CONOCIMIENTO, COL_INTERACCIONES
from pymilvus import MilvusClient, DataType
import logging

logger = logging.getLogger(__name__)

#acceso a milvus conexion
# sirve para obtener el cliente de milvus y poder hacer consultas a la base de datos
# ademas nos da la posibilidad de cambiar la conexion a milvus en un solo lugar si es necesario
_client = MilvusClient(MILVUS_DB_PATH)
_colecciones_inicializadas = False

# funcion para obtener el cliente de milvus
def get_client() -> MilvusClient:
    return _client


def asegurar_colecciones() -> None:
    """
    Verifica y crea las colecciones si no existen.
    Se ejecuta una sola vez al inicializar el cliente.
    """
    global _colecciones_inicializadas
    if _colecciones_inicializadas:
        return
    
    cliente = get_client()
    
    # Colección conocimiento: conocimiento verificado y curado
    if not cliente.has_collection(collection_name=COL_CONOCIMIENTO):
        logger.info(f"Creando colección '{COL_CONOCIMIENTO}'...")
        schema = cliente.create_schema(auto_id=True, enable_dynamic_field=False)
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="pregunta", datatype=DataType.VARCHAR, max_length=1000)
        schema.add_field(field_name="respuesta", datatype=DataType.VARCHAR, max_length=3000)
        schema.add_field(field_name="movimientos", datatype=DataType.VARCHAR, max_length=500)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=384)
        
        cliente.create_collection(collection_name=COL_CONOCIMIENTO, schema=schema)
        
        # Crear índice HNSW
        index_params = cliente.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="HNSW",
            metric_type="COSINE",
            params={"M": 16, "efConstruction": 200},
        )
        cliente.create_index(collection_name=COL_CONOCIMIENTO, index_params=index_params)
        cliente.load_collection(collection_name=COL_CONOCIMIENTO)
        logger.info(f"Colección '{COL_CONOCIMIENTO}' creada exitosamente.")
    else:
        logger.debug(f"Colección '{COL_CONOCIMIENTO}' ya existe.")
    
    # Colección interacciones: respuestas generadas por el LLM
    if not cliente.has_collection(collection_name=COL_INTERACCIONES):
        logger.info(f"Creando colección '{COL_INTERACCIONES}'...")
        schema = cliente.create_schema(auto_id=True, enable_dynamic_field=False)
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="texto_clave", datatype=DataType.VARCHAR, max_length=2000)
        schema.add_field(field_name="pregunta", datatype=DataType.VARCHAR, max_length=1000)
        schema.add_field(field_name="scene_summary", datatype=DataType.VARCHAR, max_length=1500)
        schema.add_field(field_name="respuesta", datatype=DataType.VARCHAR, max_length=3000)
        schema.add_field(field_name="movimientos", datatype=DataType.VARCHAR, max_length=500)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=384)
        
        cliente.create_collection(collection_name=COL_INTERACCIONES, schema=schema)
        
        # Crear índice HNSW
        index_params = cliente.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="HNSW",
            metric_type="COSINE",
            params={"M": 16, "efConstruction": 200},
        )
        cliente.create_index(collection_name=COL_INTERACCIONES, index_params=index_params)
        cliente.load_collection(collection_name=COL_INTERACCIONES)
        logger.info(f"Colección '{COL_INTERACCIONES}' creada exitosamente.")
    else:
        logger.debug(f"Colección '{COL_INTERACCIONES}' ya existe.")
    
    _colecciones_inicializadas = True


# Inicializar colecciones al importar
asegurar_colecciones()