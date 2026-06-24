import os
import json
from openai import OpenAI
from utils.config import OPENAI_MODEL

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def llamar_openai(prompt: str) -> dict:

    respuesta = _client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    
    contenido = respuesta.choices[0].message.content

    try:
        data = json.loads(contenido)
        return {
            "respuesta": data.get("respuesta", ""),
            "movimientos": data.get("movimientos", []),
        }
    except json.JSONDecodeError:
        return {"respuesta": contenido, "movimientos": []}


def generar_respuesta(prompt: str) -> dict:
    return llamar_openai(prompt)
