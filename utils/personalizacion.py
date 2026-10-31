"""
utils/personalizacion.py — Frases de apertura para respuestas de caché.

La respuesta cacheada NO se modifica. Aquí solo se elige, sin LLM y sin costo
de API, una frase corta que refleje el contexto visual ("veo que buscas
orientación"). La elección se hace comparando el contexto (casi siempre en
inglés) contra las situaciones de data/aperturas.json con el mismo modelo de
embeddings multilingüe que usa la base vectorial.

Si ninguna situación supera UMBRAL_APERTURA, no se devuelve nada y la
respuesta solo lleva el nombre.
"""

import json
import logging
import random

import numpy as np

from utils.config import APERTURAS_PATH, UMBRAL_APERTURA

logger = logging.getLogger(__name__)

# Se cargan una sola vez (lazy): (situacion, aperturas, matriz de embeddings)
_SITUACIONES: list[tuple[str, list[str], np.ndarray]] | None = None


def _cargar_situaciones() -> list[tuple[str, list[str], np.ndarray]]:
    global _SITUACIONES
    if _SITUACIONES is not None:
        return _SITUACIONES

    from utils.encoder.encoder import embed  # import diferido: carga el modelo

    with open(APERTURAS_PATH, "r", encoding="utf-8") as f:
        datos = json.load(f)

    situaciones = []
    for item in datos:
        vectores = np.array([embed(e) for e in item["ejemplos"]], dtype=np.float32)
        situaciones.append((item["situacion"], list(item["aperturas"]), vectores))
    _SITUACIONES = situaciones
    return _SITUACIONES


def elegir_apertura(contexto: str | None) -> str | None:
    """
    Devuelve una frase de apertura (en minúscula, sin punto final) acorde al
    contexto visual, o None si el contexto está vacío o no se parece a ninguna
    situación definida.
    """
    contexto = (contexto or "").strip()
    if not contexto:
        return None

    try:
        from utils.encoder.encoder import embed

        situaciones = _cargar_situaciones()
        v = np.array(embed(contexto), dtype=np.float32)

        mejor_sim, mejor = -1.0, None
        for nombre, aperturas, vectores in situaciones:
            sim = float(np.max(vectores @ v))  # embeddings normalizados → coseno
            if sim > mejor_sim:
                mejor_sim, mejor = sim, (nombre, aperturas)
    except Exception as exc:  # la personalización nunca debe romper la respuesta
        logger.warning("No se pudo elegir apertura de contexto: %s", exc)
        return None

    if mejor is None or mejor_sim < UMBRAL_APERTURA:
        logger.info("Apertura: sin coincidencia (sim=%.2f, umbral=%.2f)", mejor_sim, UMBRAL_APERTURA)
        return None

    logger.info("Apertura: situación=%s sim=%.2f", mejor[0], mejor_sim)
    return random.choice(mejor[1])
