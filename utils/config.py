import os
from pymilvus import MilvusClient


from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


MILVUS_DB_PATH = "utils/milvus/androide_milvus.db"

# https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2" #definido en la base vectorial, ver si lo dejamos o no

#dimension del vector definido por el modelo de embedding, ver si lo dejamos o no
EMBED_DIM = 384 

#base de datos de milvus esta es para la informacion de conocimiento osea casi toda esta es la que ingestamos con la base de datos
COL_CONOCIMIENTO = "conocimiento"
#base de datos de milvus esta es para la informacion de interacciones osea la mayoria de nuevas interacciones que haga el robot
COL_INTERACCIONES = "interacciones"


#UMBRALES DE SIMILITUD COSENO 
UMBRAL_CONOCIMIENTO = 0.35   # calibrar con pruebas tiene un mayor recall
UMBRAL_INTERACCIONES = 0.70  # calibrar con pruebas tiene una mayor precision


# parametros de busqueda para el índice HNSW en Milvus
SEARCH_PARAMS = {"metric_type": "COSINE", "params": {"ef": 64}} #este algoritmo ya lo definimos en los indices de l base vectorial

# modelos de LLM para generar respuestas
OPENAI_MODEL = "gpt-4o-mini" # el de la u pero ver si dejamos este u otro 
OLLAMA_MODEL = "llama3.2:1b" 