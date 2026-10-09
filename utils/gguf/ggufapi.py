"""
utils/gguf/ggufapi.py — Inferencia local con modelos GGUF via llama-cpp-python.

Carga el modelo indicado en config.GGUF_MODEL_PATH (por defecto
gemma-4-E2B-it-Q4_K_M.gguf) y expone la misma interfaz que gptapi:
    generar_respuesta(prompt: str) -> {"respuesta": str, "movimientos": list}
"""

import json
import logging
import os

from utils.config import GGUF_MODEL_PATH

logger = logging.getLogger(__name__)

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


# Formato de chat que usa Gemma 4 (Gemma instruction-tuned).
# El modelo solo genera cuando ve "<start_of_turn>model\n" al final.
_GEMMA_CHAT_TEMPLATE = (
    "<start_of_turn>user\n{prompt}<end_of_turn>\n"
    "<start_of_turn>model\n"
)


def llamar_gguf(prompt: str) -> dict:
    """Llama al modelo GGUF local y devuelve respuesta + movimientos.

    Se crea una instancia nueva por cada llamada para garantizar un KV cache
    completamente limpio. llama-cpp-python no libera el contexto de tokens de
    entrada con reset(), por lo que reusar la instancia hace que el contexto
    se llene tras 2-3 peticiones y el modelo deje de generar.
    """
    if not _LLAMA_DISPONIBLE:
        logger.error("llama-cpp-python no está instalado.")
        return {"respuesta": "Lo siento, el modelo local no está disponible.", "movimientos": []}
    if not os.path.isfile(GGUF_MODEL_PATH):
        logger.error("Modelo GGUF no encontrado: %s", GGUF_MODEL_PATH)
        return {"respuesta": "Lo siento, el modelo local no está disponible.", "movimientos": []}

    prompt_formateado = _GEMMA_CHAT_TEMPLATE.format(prompt=prompt)

    # Parámetros de inferencia. Se intenta hasta MAX_INTENTOS veces con semillas
    # distintas por si el modelo genera vacío (comportamiento esporádico de Gemma
    # con temperature baja y prompts largos).
    _PARAMS = [
        {"temperature": 0.3, "top_p": 0.9},
        {"temperature": 0.5, "top_p": 0.95},
        {"temperature": 0.2, "top_p": 0.85, "seed": 42},
    ]

    contenido = ""
    for intento, params in enumerate(_PARAMS, 1):
        try:
            llm = _nueva_instancia()
            output = llm(
                prompt_formateado,
                max_tokens=1024,
                stop=["<end_of_turn>"],
                **params,
            )
            raw: str = output["choices"][0]["text"]
            contenido = raw.replace("</start_of_turn>", "").strip()
            if contenido:
                break
            logger.warning("Intento %d generó vacío, reintentando…", intento)
        except Exception as exc:
            logger.error("Error en intento %d de inferencia GGUF: %s", intento, exc)

    if not contenido:
        return {
            "respuesta": "Lo siento, no puedo responder en este momento.",
            "movimientos": [],
        }

    # Intentar parsear JSON directamente
    try:
        data = json.loads(contenido)
        return {
            "respuesta": str(data.get("respuesta", contenido)),
            "movimientos": _validar_movimientos(data.get("movimientos", [])),
        }
    except json.JSONDecodeError:
        pass

    # Buscar el primer bloque JSON bien formado dentro del texto.
    # Se prueba desde el primer '{' hasta cada '}' de derecha a izquierda
    # para tolerar tokens extra que el modelo añada al final (e.g. "}\n}").
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
                pass  # Intentar con el siguiente '}' hacia la izquierda

    return {"respuesta": contenido, "movimientos": []}


def generar_respuesta(prompt: str) -> dict:
    return llamar_gguf(prompt)
