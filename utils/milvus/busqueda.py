
#aca lo de jacard y la documentacion me ayudo la ia por que la logica que tenia la cambio mucho pero el performance es mejor y la logica es mas clara y entendible
#so dejemosla asi y despues vemos si la podemos mejorar o cambiar  o algo asi
# y asi se va mejorando poco a poco


"""
busqueda_interacciones.py
=========================
Módulo de búsqueda semántica e híbrida sobre colecciones Milvus.

.. note::
    **Relación con busqueda.py**

    Este módulo implementa la misma lógica que ``busqueda.py``.
    Ambos son candidatos a consolidarse en un único módulo parametrizado,
    ya que la distinción entre colecciones (``COL_CONOCIMIENTO`` vs
    ``COL_INTERACCIONES``) está manejada por el parámetro ``coleccion``
    y los umbrales definidos en ``config.py``.

    ⚠ Pendiente de revisión arquitectónica.

Pipeline de búsqueda en dos etapas
------------------------------------
**Etapa 1 — Búsqueda vectorial (primaria):**
    Convierte el texto en un vector de embeddings y busca el registro
    más cercano usando similitud coseno sobre el índice HNSW de Milvus.
    Si el score supera el umbral recibido, retorna el resultado.

**Etapa 2 — Fallback textual híbrido:**
    Si la búsqueda vectorial no supera el umbral, evalúa todos los
    registros de la colección mediante:

    - **Coincidencia exacta / substring**: máxima prioridad (score = 1.0).
    - **Similitud de Jaccard**: sobre conjuntos de palabras normalizadas.

Sobre la similitud de Jaccard
------------------------------
Mide la superposición entre dos conjuntos de palabras::

    J(A, B) = |A ∩ B| / |A ∪ B|

    Ejemplo:
        A = {"como", "te", "llamas"}
        B = {"como", "se", "llamas", "tu"}

        J = 2 / 5 = 0.40  →  bajo umbral (0.45) → no es hit

Ventajas sobre la búsqueda vectorial pura:
    - Captura coincidencias léxicas exactas que el modelo de embeddings
      puede diluir en el espacio vectorial.
    - Útil para preguntas cortas, nombres propios o comandos técnicos.

Limitaciones conocidas:
    - No entiende sinónimos ni contexto semántico.
    - Sensible al orden y forma morfológica de las palabras.
    - El umbral (0.45) fue determinado empíricamente.

⚠ Estado de investigación:
    La incorporación de Jaccard mejoró el performance observado, pero
    introdujo cambios en la lógica del pipeline que requieren validación
    formal con el dataset real del Androide antes de considerarse estable.

    Alternativas a investigar:
        - BM25 (mejor balance léxico/semántico)
        - FTS nativo de Milvus 2.4+
        - Distancia de Levenshtein para errores tipográficos

Dependencias:
    - utils.milvus.conexion  : Singleton del cliente Milvus
    - utils.encoder.encoder  : Generación de embeddings
    - config.py              : SEARCH_PARAMS — parámetros del índice HNSW
"""

import re
import logging
import unicodedata

from utils.milvus.conexion import get_client
from utils.encoder.encoder import embed
from utils.config import SEARCH_PARAMS


# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CONSTANTES
# ---------------------------------------------------------------------------

UMBRAL_JACCARD = 0.45
"""
float: Umbral mínimo de similitud de Jaccard para aceptar un resultado
en el fallback textual.

Valor determinado empíricamente. Rango [0.0, 1.0].

⚠ Requiere validación con dataset real.
⚠ Evaluar centralizar en config.py junto a UMBRAL_CONOCIMIENTO
  y UMBRAL_INTERACCIONES.
"""

QUERY_LIMIT_FALLBACK = 1000
"""
int: Máximo de registros cargados en memoria durante el fallback de Jaccard.

⚠ Ajustar según el volumen real de las colecciones para evitar
  degradación de performance en producción.
"""


# ---------------------------------------------------------------------------
# FUNCIONES PRIVADAS
# ---------------------------------------------------------------------------

def _normalizar(texto: str) -> str:
    """
    Normaliza un texto para comparación textual robusta.

    Transforma el texto aplicando en orden:
        1. Conversión a minúsculas.
        2. Normalización Unicode NFKD (descompone caracteres compuestos).
        3. Eliminación de diacríticos (tildes, diéresis, etc.).
        4. Sustitución de puntuación por espacios.
        5. Colapso de espacios múltiples en uno solo.

    Args:
        texto (str): Texto de entrada a normalizar.

    Returns:
        str: Texto limpio, en minúsculas, sin tildes ni puntuación.

    Example:
        >>> _normalizar("¿Cómo estás, Androide?")
        'como estas androide'

        >>> _normalizar("  SEÑALAR   A   LA   DERECHA  ")
        'senalar a la derecha'
    """
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^\w\s]", " ", texto)
    return " ".join(texto.split())


def _jaccard(set_a: set, set_b: set) -> float:
    """
    Calcula la similitud de Jaccard entre dos conjuntos de palabras.

    ::

        J(A, B) = |A ∩ B| / |A ∪ B|

    Args:
        set_a (set): Palabras del primer texto.
        set_b (set): Palabras del segundo texto.

    Returns:
        float: Similitud en [0.0, 1.0].
            0.0 si alguno de los conjuntos está vacío.

    Example:
        >>> _jaccard({"hola", "como", "estas"}, {"hola", "que", "estas"})
        0.5
    """
    if not set_a or not set_b:
        return 0.0
    interseccion = len(set_a & set_b)
    union = len(set_a | set_b)
    return interseccion / union if union else 0.0


# ---------------------------------------------------------------------------
# FUNCIONES PÚBLICAS
# ---------------------------------------------------------------------------

def search(coleccion: str, texto: str, umbral: float) -> dict:
    """
    Busca el registro más relevante en una colección Milvus para un texto dado.

    Ejecuta el pipeline de dos etapas: búsqueda vectorial (primaria) y
    fallback textual híbrido (coincidencia exacta + Jaccard).

    Args:
        coleccion (str): Nombre de la colección Milvus a consultar.
            Valores esperados: ``COL_CONOCIMIENTO`` o ``COL_INTERACCIONES``
            (definidos en config.py).

        texto (str): Texto de consulta — pregunta del usuario.

        umbral (float): Umbral mínimo de similitud coseno para la etapa
            vectorial. Usar ``UMBRAL_CONOCIMIENTO`` (0.35) o
            ``UMBRAL_INTERACCIONES`` (0.70) según la colección.

    Returns:
        dict: Resultado de la búsqueda:

            .. code-block:: python

                {
                    "hit":   bool,        # True si se encontró resultado relevante
                    "score": float,       # Puntuación del mejor resultado [0.0, 1.0]
                    "data":  dict | None  # Registro con pregunta, respuesta, movimientos
                }

        El campo ``data["movimientos"]`` es un JSON string.
        Deserializar con ``json.loads()`` antes de usar.

    Raises:
        No lanza excepciones — todos los errores se capturan internamente
        y retornan ``{"hit": False, "score": 0.0, "data": None}``.

    Example:
        >>> resultado = search("conocimiento", "¿cómo te llamas?", umbral=0.35)
        >>> if resultado["hit"]:
        ...     print(resultado["data"]["respuesta"])
        ...     movimientos = json.loads(resultado["data"]["movimientos"])

    Note:
        El ``embed(texto)`` se invoca solo si la colección existe, evitando
        cómputo innecesario ante colecciones ausentes.

    TODO:
        - Consolidar con ``busqueda.py`` en un único módulo parametrizado.
        - Validar impacto real de Jaccard con el dataset del Androide.
        - Evaluar reemplazar el fallback con BM25 o FTS de Milvus 2.4+.
        - Agregar parámetro ``top_k`` para retornar múltiples candidatos.
    """
    client = get_client()
    texto_norm = _normalizar(texto)

    # --- Verificar colección antes de generar el embedding ---
    if not client.has_collection(collection_name=coleccion):
        logger.warning("Colección '%s' no encontrada en Milvus.", coleccion)
        return {"hit": False, "score": 0.0, "data": None}

    # El embedding se genera aquí (después de verificar la colección)
    # para evitar cómputo innecesario si la colección no existe.
    vector = embed(texto)

    # --- Cargar colección en memoria ---
    try:
        client.load_collection(collection_name=coleccion)
    except Exception as e:
        logger.error("Error al cargar colección '%s': %s", coleccion, e)
        return {"hit": False, "score": 0.0, "data": None}

    # =========================================================================
    # ETAPA 1: Búsqueda vectorial (primaria)
    # =========================================================================
    try:
        resultados = client.search(
            collection_name=coleccion,
            data=[vector],
            limit=1,
            output_fields=["pregunta", "respuesta", "movimientos"],
            search_params=SEARCH_PARAMS,
        )

        if resultados and resultados[0]:
            mejor = resultados[0][0]
            score = mejor.get("distance", 0.0)

            logger.debug(
                "[Vectorial] colección='%s' | score=%.4f | umbral=%.4f",
                coleccion, score, umbral,
            )

            if score >= umbral:
                logger.info("[Vectorial] Hit | score=%.4f", score)
                return {"hit": True, "score": score, "data": mejor.get("entity")}

    except Exception as e:
        logger.error("Error en búsqueda vectorial sobre '%s': %s", coleccion, e)

    # =========================================================================
    # ETAPA 2: Fallback textual híbrido (exacto + Jaccard)
    # =========================================================================
    logger.debug(
        "[Fallback] Iniciando sobre '%s' | texto_norm='%s'",
        coleccion, texto_norm,
    )

    try:
        registros = client.query(
            collection_name=coleccion,
            filter="",
            output_fields=["pregunta", "respuesta", "movimientos"],
            limit=QUERY_LIMIT_FALLBACK,
        )

        mejor_score_jaccard = 0.0
        mejor_registro = None
        palabras_texto = set(texto_norm.split())

        for reg in registros or []:
            pregunta_reg = _normalizar(reg.get("pregunta", ""))
            if not pregunta_reg:
                continue

            # --- Coincidencia exacta o substring ---
            if (
                texto_norm == pregunta_reg
                or texto_norm in pregunta_reg
                or pregunta_reg in texto_norm
            ):
                logger.info("[Fallback] Hit exacto/substring | score=1.0")
                return {"hit": True, "score": 1.0, "data": reg}

            # --- Similitud de Jaccard ---
            palabras_reg = set(pregunta_reg.split())
            score_jaccard = _jaccard(palabras_texto, palabras_reg)

            if score_jaccard > mejor_score_jaccard:
                mejor_score_jaccard = score_jaccard
                mejor_registro = reg

        if mejor_registro is not None and mejor_score_jaccard >= UMBRAL_JACCARD:
            logger.info(
                "[Fallback] Hit por Jaccard | score=%.4f", mejor_score_jaccard
            )
            return {
                "hit": True,
                "score": mejor_score_jaccard,
                "data": mejor_registro,
            }

    except Exception as e:
        logger.error("Error en fallback textual sobre '%s': %s", coleccion, e)

    # --- Sin resultados en ninguna etapa ---
    logger.debug("Sin hit en '%s' | texto='%s'", coleccion, texto[:50])
    return {"hit": False, "score": 0.0, "data": None}