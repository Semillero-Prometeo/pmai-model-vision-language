
import json
import logging
from typing import Iterable

from utils.config import COL_CONOCIMIENTO
from utils.encoder.encoder import embed
from utils.gpt.gptapi import _validar_movimientos
from utils.milvus.conexion import get_client

logger = logging.getLogger(__name__)

MOVIMIENTO_POR_DEFECTO = 1


def alimentar_basevec(items: Iterable[dict]) -> None:
    """Carga preguntas y respuestas verificadas en la memoria de conocimiento."""
    registros = []
    for item in items:
        if not isinstance(item, dict):
            raise TypeError("Cada item debe ser un diccionario.")

        pregunta = item.get("pregunta")
        respuesta = item.get("respuesta")
        if not isinstance(pregunta, str) or not pregunta.strip():
            raise ValueError("Cada item debe tener una 'pregunta' no vacía.")
        if not isinstance(respuesta, str) or not respuesta.strip():
            raise ValueError("Cada item debe tener una 'respuesta' no vacía.")

        movimientos = item.get("movimientos", item.get("movimiento", [MOVIMIENTO_POR_DEFECTO]))
        if isinstance(movimientos, int):
            movimientos = [movimientos]

        registros.append({
            "pregunta": pregunta.strip(),
            "respuesta": respuesta.strip(),
            "movimientos": json.dumps(_validar_movimientos(movimientos)),
        })

    if not registros:
        return

    preguntas = [registro["pregunta"] for registro in registros]
    for registro, vector in zip(registros, embed(preguntas)):
        registro["vector"] = vector.tolist() if hasattr(vector, "tolist") else vector

    get_client().insert(collection_name=COL_CONOCIMIENTO, data=registros)
    logger.info("Conocimiento indexado: %s registros", len(registros))
