

# este archivo es un cliente para la API de GPT,
#  que proporciona una función para generar respuestas a partir de un prompt dado usand 
# la api de gpt si se quiere cambiar de provedor se puede hacer cambiando la implementación de 
# la función _generar_respuesta.


from typing import Dict
from utils.gpt.gptapi import generar_respuesta as _generar_respuesta


def generar_respuesta(prompt: str) -> Dict:
    return _generar_respuesta(prompt)


__all__ = ["generar_respuesta"]
