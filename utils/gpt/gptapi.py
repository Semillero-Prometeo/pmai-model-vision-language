


import os
import json
from openai import OpenAI
from utils.config import OPENAI_MODEL

# usamos el cliente de OpenAI para interactuar con la API de GPT
_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))



# esta función llama a la API de OpenAI para generar una respuesta a partir de un prompt dado 
def llamar_openai(prompt: str) -> dict:

# llamamos a la API de OpenAI para generar una respuesta
#usamos el modelo  que usamos en config 
#el prompt se pasa como un mensaje de usuario
#la temperatura se establece en 0.7 para obtener respuestas más creativas :)
#el formato de respuesta se establece en json_object para que la respuesta sea un objeto JSON
    respuesta = _client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    

# obtenemos el contenido de la respuesta
    contenido = respuesta.choices[0].message.content

# intentamos decodificar el contenido como JSON y devolver un diccionario con la respuesta y los movimientos
    try:
        data = json.loads(contenido)
        return {

# si no se puede decodificar el contenido como JSON, devolvemos un diccionario con la respuesta y una lista vacía de movimientos
            "respuesta": data.get("respuesta", ""),
            "movimientos": data.get("movimientos", []),
        }
    
# si no se puede decodificar el contenido como JSON, devolvemos un diccionario con la respuesta y una lista vacía de movimientos
    except json.JSONDecodeError:
        return {"respuesta": contenido, "movimientos": []}



# esta función genera una respuesta a partir de un prompt dado usando 
# la API de OpenAI reutilizando la función llamar_openai :) 
# aca aplica la mayor parte de la logica de la funcion llamar_openai
def generar_respuesta(prompt: str) -> dict:
    return llamar_openai(prompt)
