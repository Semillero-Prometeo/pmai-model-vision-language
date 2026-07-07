
from typing import Iterable


def alimentar_basevec(items: Iterable[dict]) -> None:

	for it in items:
		if not isinstance(it, dict):
			raise TypeError("Cada item debe ser un dict con clave 'texto'.")
		if "texto" not in it:
			raise ValueError("Item sin clave 'texto' encontrada.")

	# TODO: implementar la lógica real de encoding e insert en Milvus
	return None
