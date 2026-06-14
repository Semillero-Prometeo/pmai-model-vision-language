from spanlp.palabrota import Palabrota


class DetectorGroserias:

    def __init__(self):
        self._detector = Palabrota()

    def contiene_groserias(self, texto: str) -> bool:
        if not texto:
            return False
        return self._detector.contains_palabrota(texto)

    def censurar(self, texto: str) -> str:
        if not texto:
            return texto
        return self._detector.censor(texto)