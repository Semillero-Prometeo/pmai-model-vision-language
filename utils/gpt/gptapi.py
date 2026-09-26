"""
Módulo de generación de respuestas — ahora usa Ollama en lugar de OpenAI.

La interfaz pública (_validar_movimientos, generar_respuesta) se mantiene
idéntica para no romper los módulos que la importan (indexar, context_builder…).
"""

import logging
from utils.ollama.ollamaapi import _validar_movimientos, generar_respuesta  # noqa: F401

logger = logging.getLogger(__name__)


# Re-exportar para compatibilidad con importaciones existentes
__all__ = ["_validar_movimientos", "generar_respuesta"]



#.venv/bin/python app.py