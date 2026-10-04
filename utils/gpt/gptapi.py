


import os
import json
import logging
from openai import OpenAI
from utils.config import OPENAI_MODEL

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

# Rango válido de IDs de movimientos (1 a 34 según data/movimientos.json)
MIN_MOVIMIENTO_ID = 1
MAX_MOVIMIENTO_ID = 34


def _validar_movimientos(movimientos: list) -> list:
    """
    Valida que los IDs de movimientos existan en el rango permitido.
    Deseita IDs inválidos, devuelve solo los válidos.
    
    Args:
        movimientos: Lista de IDs de movimientos
    
    Returns:
        Lista filtrada con solo IDs válidos
    """
    if not movimientos:
        return []
    
    if not isinstance(movimientos, list):
        logger.warning(f"movimientos no es lista: {type(movimientos)}")
        return []
    
    validos = []
    for mov_id in movimientos:
        try:
            id_int = int(mov_id)
            if MIN_MOVIMIENTO_ID <= id_int <= MAX_MOVIMIENTO_ID:
                validos.append(id_int)
            else:
                logger.warning(f"ID de movimiento fuera de rango: {id_int} (válido: {MIN_MOVIMIENTO_ID}-{MAX_MOVIMIENTO_ID})")
        except (ValueError, TypeError):
            logger.warning(f"ID de movimiento no es entero: {mov_id}")
    
    return validos



# esta función llama a la API de OpenAI para generar una respuesta a partir de un prompt dado 
def llamar_openai(prompt: str) -> dict:

# llamamos a la API de OpenAI para generar una respuesta
#usamos el modelo  que usamos en config 
#el prompt se pasa como un mensaje de usuario
#la temperatura se establece en 0.7 para obtener respuestas más creativas :)
#el formato de respuesta se establece en json_object para que la respuesta sea un objeto JSON
    respuesta = _get_client().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    

# obtenemos el contenido de la respuesta
    contenido = respuesta.choices[0].message.content

# intentamos decodificar el contenido como JSON y devolver un diccionario con la respuesta y los movimientos
    try:
        data = json.loads(contenido)
        movimientos_raw = data.get("movimientos", [])
        movimientos_validos = _validar_movimientos(movimientos_raw)
        
        return {
            "respuesta": data.get("respuesta", ""),
            "movimientos": movimientos_validos,  # Solo IDs válidos
        }
    
# si no se puede decodificar el contenido como JSON, devolvemos un diccionario con la respuesta y una lista vacía de movimientos
    except json.JSONDecodeError:
        return {"respuesta": contenido, "movimientos": []}



# esta función genera una respuesta a partir de un prompt dado usando 
# la API de OpenAI reutilizando la función llamar_openai :) 
# aca aplica la mayor parte de la logica de la funcion llamar_openai
def generar_respuesta(prompt: str) -> dict:
    return llamar_openai(prompt)
