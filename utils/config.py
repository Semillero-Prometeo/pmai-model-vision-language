import os
from pymilvus import MilvusClient


from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MILVUS_DB_PATH = "./androide_milvus.db"   
EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2" #definido en la base vectorial, ver si lo dejamos o no
EMBED_DIM = 384
COL_CONOCIMIENTO = "conocimiento"
COL_INTERACCIONES = "interacciones"
UMBRAL_CONOCIMIENTO = 0.70   # calibrar con pruebas
UMBRAL_INTERACCIONES = 0.70  # calibrar con pruebas
SEARCH_PARAMS = {"metric_type": "COSINE", "params": {"ef": 64}} #este algoritmo ya lo definimos en los indices de l base vectorial
OPENAI_MODEL = "gpt-4o-mini" # el de la u pero ver si dejamos este u otro 
OLLAMA_MODEL = "llama3.1:8b" #ver si dejamos este o no
