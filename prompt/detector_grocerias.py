

# Esto es un detector de grocerias  es el primer filtro que se le hace a la pregunta 
# Es de una libreria que se llama spanlp y tiene soporte para varios idiomas  
# https://github.com/jfreddypuentes/spanlp.git

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
    

    
#importamus el módulo 
_detector = DetectorGroserias()



def filtrar_pregunta(question: str) -> dict | None:

    if not question:
            return None
    if _detector.contiene_groserias(question):
            return {
                "respuesta": "Prefiero que mantengamos un trato respetuoso ¿En qué otra cosa puedo ayudarte?",
                "movimientos": [1]
            }
    return None



def procesar_pregunta(question: str) -> dict:
    if not question:
        return {"pregunta_limpia": "", "tenia_groseria": False}

    tenia_groseria = _detector.contiene_groserias(question)
    pregunta_limpia = _detector.censurar(question) if tenia_groseria else question

    return {
        "pregunta_limpia": pregunta_limpia,
        "tenia_groseria": tenia_groseria,
    }