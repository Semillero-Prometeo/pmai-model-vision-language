# Informe ejecutivo: commit `4ed033c`

**Mensaje:** `feat: update to Gemma GGUF backend with OpenAI fallback`
**Autora:** anpalopg
**Razon** Santigo por que no entendi que cambio ._.
**Alcance:** 7 archivos, +428 / −143 líneas

## Resumen

El commit cambia el motor de lenguaje del asistente R-One. Antes usaba **Ollama** (`llama3.2:1b`) o solo OpenAI. Ahora elige el motor automáticamente:

- **Con internet y `OPENAI_API_KEY`:** usa OpenAI `gpt-4o-mini`.
- **Sin internet, sin clave o si OpenAI falla:** usa **Gemma 4 E2B (GGUF)** en local, con `llama-cpp-python`.

## Cambios por archivo

| Archivo | Cambio |
|---|---|
| `utils/gguf/ggufapi.py` (nuevo, +165) | Ejecuta el modelo local. Crea una instancia nueva por llamada para evitar que el contexto se llene. Reintenta hasta 3 veces con parámetros distintos si la salida viene vacía. Extrae el JSON de la salida aunque el modelo añada texto extra. Si falta la librería o el modelo, devuelve un mensaje de disculpa y no lanza error. |
| `utils/gpt/gptapi.py` | Pasa a ser un router: comprueba la conexión con `hay_internet()` (socket a 8.8.8.8:53), usa OpenAI si puede y cae a GGUF si no. Marca el motor usado en `_backend`. Mantiene la interfaz pública. El cliente OpenAI ya no es un singleton, se crea en cada llamada. |
| `utils/config.py` | Quita `OLLAMA_MODEL`. Añade `GGUF_MODEL_PATH`, que apunta a `models/gguf/gemma-4-E2B-it-Q4_K_M.gguf`. |
| `utils/main.py` | Si la respuesta viene de caché, le antepone la etiqueta de la persona ("Nombre, …"). Añade `etiqueta` y `backend` al resultado. Limpia comentarios. |
| `app.py` | La interfaz Gradio muestra una insignia según el origen: 📦 caché, 🌐 OpenAI o 🖥️ Gemma (local). Actualiza la documentación y el encabezado. |
| `prompt/principal.py` | Reescribe el prompt. Define la identidad de R-One (nombre fijo, siempre en español, sin emojis). Añade un razonamiento en 5 pasos: persona, intención, contexto visual, movimientos y veracidad. Clasifica la intención en 7 categorías. Protege contra instrucciones inyectadas en los datos de entrada. Incluye un catálogo semántico de los 34 movimientos agrupados por función. |

## Detección de internet

- Definida en `utils/gpt/gptapi.py`, función `hay_internet()` (línea 34): conexión TCP a `8.8.8.8:53` con timeout de 2 s.
- Usada en `generar_respuesta()` (línea 88): `usar_openai = bool(api_key) and hay_internet()`.
- Observación: `socket.setdefaulttimeout(timeout)` cambia el timeout global de sockets del proceso. Se recomienda usar `s.settimeout(timeout)`.

## Puntos a revisar

1. **Modelo no versionado.** El archivo GGUF debe estar en `models/gguf/`. Si falta, el fallback local devuelve solo un mensaje de disculpa.
2. **Dependencia nueva.** Requiere `llama-cpp-python`. No se modificó `pyproject.toml` ni `requirements` en este commit.
3. **Rendimiento.** Recargar el modelo en cada petición garantiza un contexto limpio, pero añade latencia, y más con los reintentos.
4. **Detección de internet.** Depende de llegar a 8.8.8.8:53. En redes que bloquean ese puerto se usará el modelo local aunque haya conexión.
5. **Caché y etiqueta.** Si la etiqueta es "Persona no identificada", la respuesta cacheada empezará con "Persona no identificada, …".
6. **Desajuste con el prompt.** El prompt pide no usar emojis, pero la interfaz sí los usa en las insignias. Es una incoherencia menor.

## Commits anteriores (menores)

- `2f09385`: restauró la interfaz Gradio (`app.py`, +214).
- `0e7baef`: añadió un benchmark en HTML y un notebook de pruebas.
