from utils.config import MILVUS_DB_PATH
from pymilvus import MilvusClient

_client = MilvusClient(MILVUS_DB_PATH)

def get_client() -> MilvusClient:
    return _client