"""
Benchmark script — equivalent to running cells 0-16 of test.ipynb
Forces LLM calls (bypasses RAG cache) to allow real comparison between models.
Results are written to test/benchmark_resultados.csv
"""
import sys
import json
import re
import time
import logging
import statistics
import importlib
import csv
from pathlib import Path

# ── 0 · Project root ───────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
print(f"✅ Proyecto en: {ROOT}")

# ── 1 · llama-cpp-python ────────────────────────────────────────────────────────
from llama_cpp import Llama
print(f"✅ llama-cpp-python disponible ({Llama.__name__})")

# ── 2 · Config ──────────────────────────────────────────────────────────────────
GGUF_DIR = ROOT / "models" / "gguf"

CONFIG = {
    "ctx_size"    : 2048,
    "n_threads"   : 4,
    "n_gpu_layers": 10,
    "temperature" : 0.7,
    "top_p"       : 0.9,
    "top_k"       : 40,
}

MODELOS = {
    "qwen3-4b": {
        "archivo"    : GGUF_DIR / "Qwen3-4B-Q4_K_M.gguf",
        "descripcion": "Qwen3-4B Q4_K_M (~2.5 GB)",
    },
    "gemma-4-e2b": {
        "archivo"    : GGUF_DIR / "gemma-4-E2B-it-Q4_K_M.gguf",
        "descripcion": "Gemma-4 E2B Instruct Q4_K_M (~1.5 GB)",
    },
    "qwen3-1.7b": {
        "archivo"    : GGUF_DIR / "Qwen3-1.7B-Q4_K_M.gguf",
        "descripcion": "Qwen3-1.7B Q4_K_M (~1.1 GB)",
    },
}

print("\nModelos disponibles:")
for alias, info in MODELOS.items():
    existe = "✅" if info["archivo"].exists() else "❌ (no encontrado)"
    print(f"  [{alias}]  {info['descripcion']}  {existe}")

# ── 4 · GGUF engine ─────────────────────────────────────────────────────────────
_llm_activo = None
_alias_activo = None


def cargar_modelo(alias: str) -> None:
    global _llm_activo, _alias_activo
    if alias not in MODELOS:
        raise ValueError(f"Alias desconocido: '{alias}'")
    if alias == _alias_activo:
        print(f"ℹ️  [{alias}] ya está cargado.")
        return
    ruta = MODELOS[alias]["archivo"]
    if not ruta.exists():
        raise FileNotFoundError(f"Archivo GGUF no encontrado: {ruta}")
    if _llm_activo is not None:
        print(f"🔄 Descargando [{_alias_activo}] de memoria...")
        del _llm_activo
        _llm_activo = None
        _alias_activo = None
    print(f"⏳ Cargando [{alias}] — {MODELOS[alias]['descripcion']} ...")
    t0 = time.perf_counter()
    _llm_activo = Llama(
        model_path   = str(ruta),
        n_ctx        = CONFIG["ctx_size"],
        n_threads    = CONFIG["n_threads"],
        n_gpu_layers = CONFIG["n_gpu_layers"],
        verbose      = False,
    )
    _alias_activo = alias
    print(f"✅ [{alias}] cargado en {time.perf_counter() - t0:.1f}s")


def modelo_activo():
    return _alias_activo


# ── 5 · generar_respuesta GGUF ──────────────────────────────────────────────────
MIN_MOVIMIENTO_ID = 1
MAX_MOVIMIENTO_ID = 34


def _validar_movimientos(movimientos):
    if not movimientos or not isinstance(movimientos, list):
        return []
    validos = []
    for mov_id in movimientos:
        try:
            id_int = int(mov_id)
            if MIN_MOVIMIENTO_ID <= id_int <= MAX_MOVIMIENTO_ID:
                validos.append(id_int)
        except (ValueError, TypeError):
            pass
    return validos


def _extraer_json(texto: str):
    texto = texto.strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{[^{}]*"respuesta"[^{}]*\}', texto, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def generar_respuesta_gguf(prompt: str) -> dict:
    if _llm_activo is None:
        raise RuntimeError("Ningún modelo GGUF cargado.")
    salida = _llm_activo(
        prompt,
        max_tokens  = 512,
        temperature = CONFIG["temperature"],
        top_p       = CONFIG["top_p"],
        top_k       = CONFIG["top_k"],
        stop        = ["\n\n\n", "<|endoftext|>", "<|im_end|>"],
    )
    texto = salida["choices"][0]["text"]
    data  = _extraer_json(texto)
    if data:
        return {
            "respuesta"  : data.get("respuesta", ""),
            "movimientos": _validar_movimientos(data.get("movimientos", [])),
        }
    return {"respuesta": texto.strip(), "movimientos": []}


# ── 6 · Inject into RAG pipeline ────────────────────────────────────────────────
import utils.config           as config_mod
import utils.milvus.conexion  as conexion
import utils.milvus.busqueda  as busqueda
import utils.gpt.gptapi       as gptapi_module
import utils.main             as main_module

for mod in [config_mod, conexion, busqueda, gptapi_module, main_module]:
    importlib.reload(mod)

main_module.generar_respuesta = generar_respuesta_gguf

from models.schemas import GlobalObjectForContext
from prompt.principal import construir_prompt

cargar_movimientos = main_module.cargar_movimientos
secuencias         = cargar_movimientos()
print(f"✅ Pipeline RAG listo con motor GGUF.  Movimientos: {len(secuencias)}")

# ── responder_forzado: skips cache, calls LLM directly ──────────────────────────
def responder_forzado(obj, secuencias_local):
    """Same as main_module.responder but bypasses the RAG cache entirely."""
    pregunta = getattr(obj, "question", None) or ""
    from prompt.detector_grocerias import procesar_pregunta
    proc = procesar_pregunta(pregunta)
    pregunta_limpia = proc["pregunta_limpia"]
    prompt  = construir_prompt(obj, pregunta_limpia, secuencias_local)
    salida  = generar_respuesta_gguf(prompt)
    return {
        "respuesta" : str(salida["respuesta"]),
        "movimiento": salida["movimientos"][0] if salida["movimientos"] else 1,
        "fuente"    : "llm",
    }


# ── 9 · Benchmark suite ─────────────────────────────────────────────────────────
PREGUNTAS_BENCHMARK = [
    {"pregunta": "Hola R-One",                                            "tipo": "saludo"},
    {"pregunta": "¿Quién eres tú?",                                       "tipo": "identidad"},
    {"pregunta": "¿Qué es la Universidad Libre?",                         "tipo": "conocimiento"},
    {"pregunta": "¿Cuáles son los departamentos de la Universidad Libre?","tipo": "dato_especifico"},
    {"pregunta": "¿Qué es el semillero Prometeo?",                        "tipo": "conocimiento"},
    {"pregunta": "¿Cuál es el horario de la biblioteca?",                 "tipo": "dato_especifico"},
    {"pregunta": "¿Cuántas facultades tiene la universidad?",             "tipo": "dato_especifico"},
    {"pregunta": "¿Cuántos estudiantes hay hoy en el campus?",            "tipo": "sin_datos"},
    {"pregunta": "¿Puedes ser mi amigo?",                                 "tipo": "afectiva"},
]

# ── 11 · Run all 3 models ────────────────────────────────────────────────────────
todos_resultados = []

for alias in MODELOS:
    if not MODELOS[alias]["archivo"].exists():
        print(f"⚠️  [{alias}] no encontrado — se omite.")
        continue

    print(f"\n{'='*60}")
    print(f"  Evaluando: {alias}  ({MODELOS[alias]['descripcion']})")
    print(f"{'='*60}")
    cargar_modelo(alias)

    for item in PREGUNTAS_BENCHMARK:
        obj = GlobalObjectForContext(
            id_global = "bench",
            etiqueta  = "Evaluador",
            confianza = 0.99,
            contexto  = "Entorno de prueba",
            question  = item["pregunta"],
        )
        t0       = time.perf_counter()
        resultado = responder_forzado(obj, secuencias)
        latencia  = time.perf_counter() - t0

        todos_resultados.append({
            "modelo"    : alias,
            "tipo"      : item["tipo"],
            "pregunta"  : item["pregunta"],
            "respuesta" : resultado["respuesta"],
            "movimiento": resultado["movimiento"],
            "fuente"    : resultado["fuente"],
            "latencia_s": round(latencia, 3),
        })
        print(f"  🟢 llm  [{latencia:.2f}s]  {item['pregunta'][:60]}")

# ── Export CSV ───────────────────────────────────────────────────────────────────
csv_path = ROOT / "test" / "benchmark_resultados.csv"
if todos_resultados:
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=todos_resultados[0].keys())
        writer.writeheader()
        writer.writerows(todos_resultados)
    print(f"\n✅ CSV guardado en: {csv_path}")

# ── Summary ──────────────────────────────────────────────────────────────────────
print("\n\n📊 RESUMEN POR MODELO (llamadas LLM directas)")
print("=" * 70)
for alias in MODELOS:
    filas = [r for r in todos_resultados if r["modelo"] == alias]
    if not filas:
        continue
    llm_lat = [r["latencia_s"] for r in filas]
    print(f"\n  {alias}  —  {MODELOS[alias]['descripcion']}")
    print(f"    Preguntas evaluadas : {len(filas)}")
    print(f"    Latencia LLM        : min={min(llm_lat):.2f}s  max={max(llm_lat):.2f}s  "
          f"media={statistics.mean(llm_lat):.2f}s  mediana={statistics.median(llm_lat):.2f}s")

print("\n\n📋 RESULTADOS DETALLADOS")
print("=" * 70)
for r in todos_resultados:
    print(f"\n[{r['modelo']}] [{r['latencia_s']:.2f}s] tipo={r['tipo']}")
    print(f"  Pregunta : {r['pregunta']}")
    print(f"  Mov      : {r['movimiento']}")
    print(f"  Respuesta: {r['respuesta'][:200]}")
