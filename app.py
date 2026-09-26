"""
app.py — Interfaz gráfica para probar R-One en tiempo real.

Ejecutar:
    .venv/bin/python app.py

NOTA: usar siempre el intérprete del venv, NO `uv run`, para evitar un bug
de pathlib en el cpython-3.12.14 gestionado por uv.

Requiere que Ollama esté corriendo localmente con el modelo configurado en
utils/config.py (OLLAMA_MODEL, por defecto llama3.2:1b).
"""

import re
import subprocess
import tempfile
import gradio as gr

import utils.main as main_module
from models.schemas import GlobalObjectForContext

# ── TTS con voz del sistema macOS ─────────────────────────────────────────────
_TTS_VOICE = "Paulina"  # voz en español (es_MX); cambia a "Mónica" para es_ES


def _texto_a_wav(texto: str) -> str | None:
    """Convierte texto a WAV usando `say` + `afconvert` (macOS).

    Devuelve la ruta al archivo WAV temporal, o None si falla.
    Elimina caracteres markdown (* _ ` #) que la voz leería literalmente.
    """
    texto_limpio = re.sub(r"[*_`#]", "", texto).strip()
    if not texto_limpio:
        return None
    try:
        aiff = tempfile.NamedTemporaryFile(suffix=".aiff", delete=False)
        wav  = tempfile.NamedTemporaryFile(suffix=".wav",  delete=False)
        aiff.close()
        wav.close()
        subprocess.run(
            ["say", "-v", _TTS_VOICE, "-o", aiff.name, texto_limpio],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["afconvert", aiff.name, wav.name, "-d", "LEI16", "-f", "WAVE"],
            check=True, capture_output=True,
        )
        return wav.name
    except Exception:
        return None

# ── Carga inicial de secuencias de movimientos ────────────────────────────────
secuencias = main_module.cargar_movimientos()

# ── Mapa id → nombre para mostrar en la UI ───────────────────────────────────
_MOV_NOMBRE: dict[int, str] = {m["id"]: m["name"] for m in secuencias}


def _formatear_movimientos(mov_id: int) -> str:
    """Devuelve una representación legible del movimiento resultante."""
    nombre = _MOV_NOMBRE.get(mov_id, "Desconocido")
    return f"🤖 Movimiento #{mov_id} — {nombre}"


# ── Función principal del pipeline ───────────────────────────────────────────
def procesar(
    pregunta: str,
    etiqueta: str,
    confianza: float,
    contexto_visual: str,
    historial: list[dict],
) -> tuple[list[dict], str, str, str | None]:
    """
    Ejecuta el pipeline completo y devuelve el historial actualizado,
    la respuesta, el movimiento sugerido y la ruta al WAV con la voz.
    """
    pregunta = (pregunta or "").strip()
    if not pregunta:
        return historial, "", "", None

    obj = GlobalObjectForContext(
        id_global="ui-1",
        etiqueta=etiqueta or "Visitante",
        confianza=float(confianza),
        contexto=contexto_visual or None,
        question=pregunta,
    )

    resultado = main_module.responder(obj, secuencias)

    respuesta: str = resultado.get("respuesta", "")
    mov_id: int = resultado.get("movimiento", 1)
    fuente: str = resultado.get("fuente", "llm")
    fuente_badge = "📦 caché" if fuente == "cache" else "🧠 Ollama"

    historial = historial + [
        {"role": "user",      "content": pregunta},
        {"role": "assistant", "content": f"{respuesta}\n\n*Fuente: {fuente_badge}*"},
    ]

    mov_texto = _formatear_movimientos(mov_id)
    audio_path = _texto_a_wav(respuesta)
    return historial, "", mov_texto, audio_path


def limpiar(historial):
    return [], "", "", None


# ── Interfaz Gradio ───────────────────────────────────────────────────────────
with gr.Blocks(title="R-One — Demo en tiempo real") as demo:
    gr.Markdown(
        """
        # 🤖 R-One — Demo en tiempo real
        Asistente del semillero **Prometeo** · Universidad Libre  
        _Modelo: Ollama local (`llama3.2:1b` por defecto)_
        """
    )

    with gr.Row():
        # ── Panel izquierdo: parámetros de contexto ───────────────────────────
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ Contexto de la escena")
            etiqueta_inp = gr.Textbox(
                label="Nombre / etiqueta de la persona detectada",
                placeholder="Ej: Andrea, Visitante, Estudiante…",
                value="Visitante",
            )
            confianza_inp = gr.Slider(
                label="Confianza de detección (0–1)",
                minimum=0.0, maximum=1.0, step=0.01, value=0.70,
            )
            contexto_inp = gr.Textbox(
                label="Contexto visual (descripción de la escena)",
                placeholder="Ej: Mujer sonriendo frente a la cámara",
                lines=3,
            )
            gr.Markdown("---")
            gr.Markdown(
                "**Consejos:**\n"
                "- Deja el contexto visual vacío si no hay cámara.\n"
                "- El etiquetado afecta el tono de la respuesta.\n"
                "- Las respuestas se cachean en Milvus automáticamente."
            )

        # ── Panel derecho: chat ───────────────────────────────────────────────
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(
                label="Conversación con R-One",
                height=460,
            )

            with gr.Row():
                pregunta_inp = gr.Textbox(
                    label="Tu pregunta",
                    placeholder="Escribe aquí y presiona Enter o el botón Enviar…",
                    lines=1,
                    scale=4,
                    show_label=False,
                )
                enviar_btn = gr.Button("Enviar ↵", variant="primary", scale=1)

            movimiento_out = gr.Textbox(
                label="Movimiento sugerido para el robot",
                interactive=False,
            )

            audio_out = gr.Audio(
                label="🔊 Voz de R-One",
                type="filepath",
                autoplay=True,
                interactive=False,
            )

            limpiar_btn = gr.Button("🗑️ Limpiar conversación", variant="secondary")

    # ── Historial de estado ───────────────────────────────────────────────────
    historial_state = gr.State([])

    # ── Bindings ─────────────────────────────────────────────────────────────
    enviar_btn.click(
        fn=procesar,
        inputs=[pregunta_inp, etiqueta_inp, confianza_inp, contexto_inp, historial_state],
        outputs=[chatbot, pregunta_inp, movimiento_out, audio_out],
    ).then(
        fn=lambda h: h,
        inputs=[chatbot],
        outputs=[historial_state],
    )

    pregunta_inp.submit(
        fn=procesar,
        inputs=[pregunta_inp, etiqueta_inp, confianza_inp, contexto_inp, historial_state],
        outputs=[chatbot, pregunta_inp, movimiento_out, audio_out],
    ).then(
        fn=lambda h: h,
        inputs=[chatbot],
        outputs=[historial_state],
    )

    limpiar_btn.click(
        fn=limpiar,
        inputs=[historial_state],
        outputs=[chatbot, pregunta_inp, movimiento_out, audio_out],
    ).then(
        fn=lambda _: [],
        inputs=[chatbot],
        outputs=[historial_state],
    )


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False, theme=gr.themes.Soft())
