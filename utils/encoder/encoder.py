from sentence_transformers import SentenceTransformer
from utils.config import EMBED_MODEL_NAME

#usamos el mismo que el de la ingesta si lo cambiamos ahi lo cambiamos acá también porfavorr

_modelo = SentenceTransformer(EMBED_MODEL_NAME)

def embed(texto: str) -> list[float]:
    return _modelo.encode(texto, normalize_embeddings=True).tolist()