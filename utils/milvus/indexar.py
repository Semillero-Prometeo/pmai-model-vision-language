

import json
import logging
from utils.milvus.conexion import get_client
from utils.encoder.encoder import embed
from utils.config import COL_CONOCIMIENTO, COL_INTERACCIONES
from utils.gpt.gptapi import _validar_movimientos

logger = logging.getLogger(__name__)

# esta función indexa una pregunta, respuesta y movimientos en Milvus.
# por defecto usa la colección de conocimiento, pero puede apuntar a interacciones.

def _extraer_palabras_clave(texto: str, num_palabras: int = 5) -> str:
    """
    Extrae las primeras palabras clave de un texto.
    Útil para generar el campo `texto_clave` de la colección de interacciones.
    """
    palabras = texto.split()[:num_palabras]
    return " ".join(palabras)


def indexar(
    pregunta: str,
    respuesta: str,
    movimientos: list = None,
    collection_name: str = COL_CONOCIMIENTO,
    scene_summary: str = None,
) -> None:
    """
    Indexa una pregunta, respuesta y movimientos en Milvus.
    
    IMPORTANTE: Valida y filtra los IDs de movimientos antes de guardar.
    Solo guarda movimientos con IDs válidos (1-34).
    
    Args:
        pregunta: Texto de la pregunta
        respuesta: Texto de la respuesta
        movimientos: Lista de IDs de movimientos (se valida y convierte a JSON)
        collection_name: Colección destino (conocimiento o interacciones)
        scene_summary: Resumen de escena (solo para interacciones)
    """
    if movimientos is None:
        movimientos = []

    client = get_client()
    
    # VALIDAR movimientos antes de guardar
    movimientos_validos = _validar_movimientos(movimientos)
    if movimientos != movimientos_validos:
        logger.warning(
            f"Movimientos inválidos detectados. Original: {movimientos}, "
            f"Válidos: {movimientos_validos}"
        )
    
    # Preparar datos base
    data_dict = {
        "pregunta":    pregunta,
        "respuesta":   respuesta,
        "movimientos": json.dumps(movimientos_validos),  # Guardar solo válidos
        "vector":      embed(pregunta),          
    }
    
    # Si es colección de interacciones, agregar campos adicionales
    if collection_name == COL_INTERACCIONES:
        data_dict["texto_clave"] = _extraer_palabras_clave(pregunta)
        data_dict["scene_summary"] = scene_summary or pregunta[:500]  # Limitar a 500 chars

    data = [data_dict]
    client.insert(collection_name=collection_name, data=data)
    logger.info(f"Indexado en '{collection_name}': {len(movimientos_validos)} movimientos válidos")