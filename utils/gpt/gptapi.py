"""
utils/gpt/gptapi.py — Router de LLM con fallback automático.

Estrategia:
  1. Si hay OPENAI_API_KEY en el entorno → intenta OpenAI (gpt-4o-mini).
  2. Si no hay clave, o la llamada falla → modelo GGUF local
     (gemma-4-E2B-it-Q4_K_M.gguf) via llama-cpp-python.

La interfaz pública (generar_respuesta, _validar_movimientos) se mantiene
idéntica para no romper los módulos que la importan.
"""

import json
import logging
import os
import socket

from openai import OpenAI

from utils.config import OPENAI_MODEL
from utils.gguf.ggufapi import (
    _validar_movimientos,
    generar_respuesta as _generar_respuesta_gguf,
)

logger = logging.getLogger(__name__)

__all__ = ["_validar_movimientos", "generar_respuesta", "hay_internet"]


def hay_internet(host: str = "api.openai.com", puerto: int = 443, timeout: float = 2.0) -> bool:
    """Sonda opcional para logs. No decide el backend de generar_respuesta."""
    try:
        socket.setdefaulttimeout(timeout)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, puerto))
        return True
    except OSError:
        return False


def llamar_openai(prompt: str) -> dict:
    """Llama a la API de OpenAI y devuelve respuesta + movimientos."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY no está definida en el entorno.")

    client = OpenAI(api_key=api_key)

    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        contenido: str = completion.choices[0].message.content or ""
    except Exception as exc:
        logger.error("Error llamando a OpenAI: %s", exc)
        raise

    try:
        data = json.loads(contenido)
        return {
            "respuesta": str(data.get("respuesta", contenido)),
            "movimientos": _validar_movimientos(data.get("movimientos", [])),
        }
    except json.JSONDecodeError:
        return {"respuesta": contenido, "movimientos": []}


def generar_respuesta(prompt: str) -> dict:
    """
    Genera una respuesta con OpenAI si hay API key, o Gemma 4 E2B si no.

    El campo extra ``_backend`` indica qué motor se usó:
      "openai" | "gguf"
    """
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()

    if api_key:
        try:
            resultado = llamar_openai(prompt)
            resultado["_backend"] = "openai"
            logger.info("Respuesta generada con OpenAI (%s)", OPENAI_MODEL)
            return resultado
        except Exception as exc:
            logger.warning(
                "OpenAI falló (%s) — usando modelo GGUF local como fallback.", exc
            )

    resultado = _generar_respuesta_gguf(prompt)
    resultado["_backend"] = "gguf"
    logger.info("Respuesta generada con modelo GGUF local (Gemma 4 E2B)")
    return resultado
