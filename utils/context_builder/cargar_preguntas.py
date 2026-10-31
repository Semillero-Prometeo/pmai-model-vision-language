"""Carga el JSON de preguntas en la colección conocimiento.

En la Jetson, desde la raíz de este repositorio:

    PYTHONPATH=. python -m utils.context_builder.cargar_preguntas

No vuelve a insertar una pregunta que ya esté guardada con el mismo texto.
"""

import json
from pathlib import Path

from utils.config import COL_CONOCIMIENTO
from utils.context_builder.alimentar_basevec import alimentar_basevec
from utils.milvus.conexion import get_client

JSON_PREGUNTAS = (
    Path(__file__).resolve().parents[1]
    / "webscraping"
    / "primera fase"
    / "preguntas_respuestas.json"
)


def cargar(path: Path = JSON_PREGUNTAS) -> int:
    items = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise ValueError(f"{path} debe ser una lista de preguntas.")

    client = get_client()
    rows = client.query(
        collection_name=COL_CONOCIMIENTO,
        filter="id >= 0",
        output_fields=["pregunta"],
        limit=16384,
    )
    ya = {str(row.get("pregunta", "")).strip() for row in rows}
    nuevos = [item for item in items if str(item.get("pregunta", "")).strip() not in ya]
    if nuevos:
        alimentar_basevec(nuevos)
    return len(nuevos)


if __name__ == "__main__":
    insertadas = cargar()
    print(f"Conocimiento nuevo: {insertadas}")
