# utils/ollama/reformular.py
import ollama
from utils.config import OLLAMA_MODEL


def reformular(texto: str) -> str:
    prompt = f"""Reformula el texto con palabras diferentes SIN cambiar el significado.
NO inventes información, profesiones, nombres ni datos. Mantén los mismos hechos.

Ejemplo:
Original: "Hola, soy un robot."
Reformulado: "Saludos, soy una máquina."

Original: "{texto}"
Reformulado:"""

    resultado = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={
            "num_predict": 150,
            "temperature": 0.1,    # ← clave anti-invención
        },
    )
    return resultado["message"]["content"].strip()