import json
import logging
import ollama
from utils.config import OLLAMA_MODEL

logger = logging.getLogger(__name__)

# Rango válido de IDs de movimientos (1 a 34 según data/movimientos.json)
MIN_MOVIMIENTO_ID = 1
MAX_MOVIMIENTO_ID = 34


def _validar_movimientos(movimientos: list) -> list:
    """Valida que los IDs de movimientos estén en el rango permitido."""
    if not movimientos:
        return []
    if not isinstance(movimientos, list):
        logger.warning("movimientos no es lista: %s", type(movimientos))
        return []
    validos = []
    for mov_id in movimientos:
        try:
            id_int = int(mov_id)
            if MIN_MOVIMIENTO_ID <= id_int <= MAX_MOVIMIENTO_ID:
                validos.append(id_int)
            else:
                logger.warning(
                    "ID de movimiento fuera de rango: %d (válido: %d-%d)",
                    id_int, MIN_MOVIMIENTO_ID, MAX_MOVIMIENTO_ID,
                )
        except (ValueError, TypeError):
            logger.warning("ID de movimiento no es entero: %s", mov_id)
    return validos


def llamar_ollama(prompt: str) -> dict:
    """Llama al modelo Ollama local y devuelve respuesta + movimientos.

    Ollama no soporta ``response_format`` JSON nativo en todas las versiones,
    así que se extrae el primer bloque JSON del texto generado.
    """
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.7},
            format="json",
        )
        contenido: str = response["message"]["content"]
    except Exception as exc:
        logger.error("Error llamando a Ollama: %s", exc)
        return {"respuesta": "Lo siento, no puedo responder en este momento.", "movimientos": []}

    # Intentar parsear JSON directamente
    try:
        data = json.loads(contenido)
        movimientos_raw = data.get("movimientos", [])
        return {
            "respuesta": str(data.get("respuesta", contenido)),
            "movimientos": _validar_movimientos(movimientos_raw),
        }
    except json.JSONDecodeError:
        pass

    # Extraer primer bloque JSON del texto si el modelo no devolvió JSON puro
    start = contenido.find("{")
    end = contenido.rfind("}") + 1
    if start != -1 and end > start:
        try:
            data = json.loads(contenido[start:end])
            movimientos_raw = data.get("movimientos", [])
            return {
                "respuesta": str(data.get("respuesta", contenido)),
                "movimientos": _validar_movimientos(movimientos_raw),
            }
        except json.JSONDecodeError:
            pass

    return {"respuesta": contenido, "movimientos": []}


def generar_respuesta(prompt: str) -> dict:
    return llamar_ollama(prompt)
