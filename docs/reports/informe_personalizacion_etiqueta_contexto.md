# Informe: personalización de respuestas (etiqueta de nombre y contexto visual)

**Estado:** cambios sin commit en el árbol de trabajo
**Archivos modificados:** `prompt/principal.py`, `utils/main.py`, `utils/config.py`
**Archivos nuevos:** `utils/personalizacion.py`, `data/aperturas.json`

> Informe nuevo e independiente de `informe_commit_4ed033c.md`, que describe el commit anterior.

## 1. Objetivo

Lograr que R-One use la **etiqueta de la persona** y el **contexto visual** (captioning) en sus respuestas, con tres condiciones:

1. Que funcione igual con OpenAI y con Gemma local.
2. Que el nombre no se guarde en la base vectorial y que "Persona no identificada" nunca se diga ni se guarde.
3. Que las respuestas de caché se personalicen **sin modificar su contenido y sin usar un LLM** (para no gastar API).

## 2. Problemas detectados

| # | Problema | Causa |
|---|---|---|
| 1 | OpenAI y Gemma ignoraban a veces la etiqueta y el contexto | El prompt los trataba como opcionales ("personaliza", "ignóralos si no aportan"). Los datos estaban al principio, a unas 140 líneas del punto de generación. Siete de los nueve ejemplos mostraban respuestas sin nombre ni contexto. |
| 2 | El nombre se guardaba en Milvus | El LLM escribe "Andrea, …" en la respuesta y esa respuesta se indexaba tal cual en `COL_INTERACCIONES`. |
| 3 | Otra persona recibía el nombre equivocado desde la caché | Consecuencia del punto 2: la respuesta cacheada ya traía el nombre de quien la generó. |
| 4 | "Persona no identificada" se anteponía a las respuestas de caché | `responder()` anteponía la etiqueta siempre, incluso cuando era la marca por defecto. |
| 5 | Mayúscula incorrecta tras el nombre en caché | "Pedro, El sol…" en vez de "Pedro, el sol…". |

## 3. Cambios realizados

### 3.1 Prompt (`prompt/principal.py`)

- **Datos de entrada al final.** `<datos_de_entrada>` pasó del inicio al final, junto al punto de generación, y se añadió una línea **RECUERDA** que repite la etiqueta.
- **Bloque "PERSONALIZACIÓN OBLIGATORIA"** como primera sección de `<reglas>`: usar el nombre, reflejar el contexto visual y cuándo omitirlo.
- **Razonamiento conservado.** Se mantuvieron las instrucciones detalladas sobre etiqueta y contexto visual (estado emocional, situación física, idioma, qué hacer si es ambiguo).
- **Ejemplos reescritos.** Cada uno muestra `PERSONA | CONTEXTO | PREGUNTA`; siete usan el nombre y tres reflejan el contexto.
- **Catálogo duplicado eliminado.** Se quitó `{catalogo_movimientos}`; la guía semántica fija cubre los 34 movimientos. `construir_prompt()` mantiene su firma pero ya no usa `secuencias`.
- **"Persona no identificada"** se mantiene como etiqueta por defecto, con una regla que la define como marca interna que nunca se menciona en la respuesta.

### 3.2 Nombre fuera de la base vectorial (`utils/main.py`)

- `_quitar_nombre()` elimina el nombre de la respuesta justo antes de `indexar()`. Cubre "Andrea, …", "¡Hola, Andrea!" y "…, Daniel.", con la etiqueta completa y cada palabra de 3 o más letras.
- Si después de limpiar el nombre sigue apareciendo, la interacción **no se indexa**.
- `_etiqueta_real()` y `_limpiar_sin_nombre()` tratan "Persona no identificada" como "sin nombre": se quita de la respuesta al usuario, no se antepone en caché y su presencia impide indexar.
- `_anteponer_nombre()` ajusta la mayúscula inicial ("Pedro, el sol…") sin tocar siglas ni nombres propios (R-One, UNAL, Prometeo, Universidad).

### 3.3 Personalización de caché sin LLM (`utils/personalizacion.py`, `data/aperturas.json`)

La respuesta cacheada llega **intacta**. Solo se antepone una frase de apertura corta:

```
contexto visual ─embed─► comparado con 41 situaciones ─► la más parecida
        │ si similitud < 0.60 → solo el nombre
        ▼
"Andrea, parece que necesitas una mano para ubicarte. <respuesta de caché intacta>"
```

- Usa el mismo modelo de embeddings multilingüe que la base vectorial (`paraphrase-multilingual-MiniLM-L12-v2`), así que entiende captions en inglés.
- **Costo de API: cero.** No hay carga de Gemma ni llamada a GPT.
- Si el cálculo falla, devuelve `None` y la respuesta sale sin apertura.
- `data/aperturas.json`: **41 situaciones, 158 ejemplos de comparación y 103 frases de apertura**, editable sin tocar código.
- Las frases no llevan género fijo ni signos de admiración o interrogación.

Casos cubiertos: emociones (sonrisa, alegría, sorpresa, frustración, nervios, cansancio, curiosidad), comportamiento (prisa, acercamiento, espera, sentado, señalando, mano levantada, brazos cruzados), objetos (mochila, portátil, lectura, celular, fotos, audífonos, café, ropa deportiva), personas (niño, adulto mayor, grupo, conversando, uniforme, evento, mascota), ropa y clima (gafas, gorra, abrigo, calor, paraguas) y orientación.

### 3.4 Configuración (`utils/config.py`)

| Constante | Valor | Uso |
|---|---|---|
| `APERTURAS_PATH` | `data/aperturas.json` | Ruta del catálogo de situaciones |
| `UMBRAL_APERTURA` | `0.60` | Similitud coseno mínima para añadir una apertura |

## 4. Resultado esperado

| Caso | Respuesta al usuario | Guardado en Milvus |
|---|---|---|
| LLM, Andrea, sin contexto | `Andrea, el sol se ve amarillo porque…` | `El sol se ve amarillo porque…` |
| LLM, sin nombre | `El sol se ve amarillo porque…` | igual |
| Caché, Pedro, contexto "child staring at the robot" | `Pedro, me alegra que los más pequeños quieran conocerme. El sol se ve amarillo…` | no se guarda |
| Caché, Andrea, contexto irrelevante | `Andrea, el sol se ve amarillo porque…` | no se guarda |
| Caché, sin nombre, sin contexto | `El sol se ve amarillo porque…` | no se guarda |

## 5. Validación

| Prueba | Resultado |
|---|---|
| Sintaxis de los módulos modificados | Correcta |
| `construir_prompt()` con etiqueta real, vacía y "Persona no identificada" | Correcto |
| Guía de movimientos del prompt vs `data/movimientos.json` | 34 de 34 coinciden |
| `_quitar_nombre()` y `_limpiar_sin_nombre()` con 10 casos | Correcto |
| `_anteponer_nombre()` con 11 casos | Correcto |
| Selección de situación con 20 contextos relevantes | **20 de 20** (similitud mínima 0.69) |
| Contextos irrelevantes (10) | Similitud máxima 0.55, todos por debajo del umbral 0.60 |

## 6. Limitaciones y riesgos

1. **No se probó con modelos reales de lenguaje.** No se ejecutó OpenAI ni Gemma con el prompt nuevo. `llama-cpp-python` y el archivo GGUF no están en este entorno. Que Gemma use siempre nombre y contexto sigue siendo una hipótesis.
2. **No se probó contra Milvus.** La limpieza e indexación se verificaron a nivel de funciones.
3. **Umbral calibrado con contextos propios.** Los 30 contextos de prueba fueron escritos para esta validación, no vienen de la cámara. Conviene recalibrar `UMBRAL_APERTURA` con captions reales.
4. **`data/` está en `.gitignore`.** `data/aperturas.json` (y `data/movimientos.json`) **no se versionan**. Hay que quitar `data/` del `.gitignore` o forzar el añadido con `git add -f` para que el archivo llegue al repositorio.
5. **Datos viejos en Milvus.** Las entradas ya guardadas con nombres reales no se limpian. En la lectura de caché solo se les quita "Persona no identificada".
6. **Catálogo de movimientos fijo en el prompt.** Si cambia `data/movimientos.json`, hay que actualizar el prompt a mano.
7. **Carga inicial.** La primera consulta con contexto carga 158 ejemplos en el modelo de embeddings y tarda un poco más.
8. **Interfaz.** `app.py` usa "Visitante" como etiqueta por defecto, por lo que ahí sí se vería "Visitante, …".

## 7. Siguientes pasos recomendados

1. Probar el prompt con OpenAI y con Gemma usando etiquetas y contextos reales de la cámara.
2. Recalibrar `UMBRAL_APERTURA` con captions reales.
3. Resolver el `.gitignore` de `data/` antes del commit.
4. Decidir si se limpian las entradas viejas de Milvus (script de limpieza o borrado).
5. Cambiar la etiqueta por defecto "Visitante" de `app.py` para que no se diga al usuario.
6. Precargar las situaciones al arrancar si la primera consulta resulta lenta.
