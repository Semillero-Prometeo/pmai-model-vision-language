from typing import Dict
from utils.gpt.gptapi import generar_respuesta as _generar_respuesta

def generar_respuesta(prompt: str) -> Dict:
    return _generar_respuesta(prompt)


__all__ = ["generar_respuesta"]
