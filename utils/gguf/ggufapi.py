"""
utils/gguf/ggufapi.py — Inferencia local con modelos GGUF via llama-cpp-python.

Carga el modelo indicado en config.GGUF_MODEL_PATH (por defecto
gemma-4-E2B-it-Q4_K_M.gguf) y expone la misma interfaz que gptapi:
    generar_respuesta(prompt: str) -> {"respuesta": str, "movimientos": list}
"""

import json
import logging
import os
import threading

from utils.config import GGUF_MODEL_PATH

logger = logging.getLogger(__name__)

_APOLOGY = {
    "respuesta": "Lo siento, no puedo responder en este momento.",
    "movimientos": [],
}


def _validar_movimientos(movimientos: list, permitidos: set[int] | None = None) -> list:
    if not movimientos or not isinstance(movimientos, list):
        return []
    validos = []
    for mov_id in movimientos:
        try:
            id_int = int(mov_id)
        except (TypeError, ValueError):
            continue
        if permitidos is not None and id_int not in permitidos:
            continue
        validos.append(id_int)
    return validos


try:
    from llama_cpp import Llama as _Llama  # type: ignore
    _LLAMA_DISPONIBLE = True
except ImportError:
    _LLAMA_DISPONIBLE = False


_llm = None
_lock = threading.Lock()


def _nueva_instancia() -> "_Llama":
    """Crea una instancia fresca del modelo con KV cache vacío."""
    if not _LLAMA_DISPONIBLE:
        raise ImportError(
            "llama-cpp-python no está instalado. "
            "Ejecuta: uv add llama-cpp-python"
        )
    if not os.path.isfile(GGUF_MODEL_PATH):
        raise FileNotFoundError(
            f"Modelo GGUF no encontrado en: {GGUF_MODEL_PATH}\n"
            "Descárgalo y colócalo en models/gguf/ o ajusta GGUF_MODEL_PATH en config.py"
        )
    logger.info("Cargando modelo GGUF desde %s …", GGUF_MODEL_PATH)
    return _Llama(
        model_path=GGUF_MODEL_PATH,
        n_ctx=8192,
        n_threads=os.cpu_count() or 4,
        verbose=False,
    )


def _obtener_o_crear() -> "_Llama":
    global _llm
    if _llm is None:
        _llm = _nueva_instancia()
    return _llm


def _descartar() -> None:
    global _llm
    _llm = None


def precargar() -> None:
    """Precarga el modelo GGUF en memoria; no interrumpe el arranque si falla."""
    with _lock:
        try:
            _obtener_o_crear()
        except ImportError:
            logger.error("llama-cpp-python no está instalado.")
        except FileNotFoundError:
            logger.error("Modelo GGUF no encontrado: %s", GGUF_MODEL_PATH)


# Formato de chat que usa Gemma 4 (Gemma instruction-tuned).
# El modelo solo genera cuando ve "<start_of_turn>model\n" al final.
_GEMMA_CHAT_TEMPLATE = (
    "<start_of_turn>user\n{prompt}<end_of_turn>\n"
    "<start_of_turn>model\n"
)


def _parsear_contenido(contenido: str) -> dict:
    try:
        data = json.loads(contenido)
        return {
            "respuesta": str(data.get("respuesta", contenido)),
            "movimientos": _validar_movimientos(data.get("movimientos", [])),
        }
    except json.JSONDecodeError:
        pass

    start = contenido.find("{")
    if start != -1:
        pos = len(contenido)
        while True:
            pos = contenido.rfind("}", start, pos)
            if pos == -1:
                break
            candidato = contenido[start:pos + 1]
            try:
                data = json.loads(candidato)
                return {
                    "respuesta": str(data.get("respuesta", contenido)),
                    "movimientos": _validar_movimientos(data.get("movimientos", [])),
                }
            except json.JSONDecodeError:
                pass

    return {"respuesta": contenido, "movimientos": []}


def llamar_gguf(prompt: str) -> dict:
    """Llama al modelo GGUF local y devuelve respuesta + movimientos."""
    if not _LLAMA_DISPONIBLE:
        logger.error("llama-cpp-python no está instalado.")
        return dict(_APOLOGY)
    if not os.path.isfile(GGUF_MODEL_PATH):
        logger.error("Modelo GGUF no encontrado: %s", GGUF_MODEL_PATH)
        return dict(_APOLOGY)

    prompt_formateado = _GEMMA_CHAT_TEMPLATE.format(prompt=prompt)

    with _lock:
        for intento in (1, 2):
            llm = _obtener_o_crear()
            llm.reset()
            output = llm(
                prompt_formateado,
                max_tokens=1024,
                stop=["<end_of_turn>"],
                temperature=0.3,
                top_p=0.9,
            )
            raw: str = output["choices"][0]["text"]
            contenido = raw.replace("</start_of_turn>", "").strip()
            if contenido:
                return _parsear_contenido(contenido)
            if intento == 1:
                logger.warning("Generación vacía, reconstruyendo instancia…")
                _descartar()

        return dict(_APOLOGY)


def generar_respuesta(prompt: str) -> dict:
    return llamar_gguf(prompt)
