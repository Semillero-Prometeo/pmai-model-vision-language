# utils/gpt/cliente.py
import os
from openai import OpenAI
from utils.config import OPENAI_MODEL

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generar_respuesta(prompt: str) -> dict:
    return llamar_openai(prompt)
