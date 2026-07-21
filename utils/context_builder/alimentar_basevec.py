
from typing import Iterable


#funcion para alimentar la base de vectores con los items que se le pasen es como un decodificador de los items que se le pasan y los inserta en la base de vectores
def alimentar_basevec(items: Iterable[dict]) -> None:

	for it in items:
		if not isinstance(it, dict):
			raise TypeError("Cada item debe ser un dict con clave 'texto'.")
		if "texto" not in it:
			raise ValueError("Item sin clave 'texto' encontrada.")


	# TODO: implementar la lógica real de encoding e insert en Milvus
	return None
