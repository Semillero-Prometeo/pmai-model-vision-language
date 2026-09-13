# pmai-model-vision-language
PROMETEO — Multimodal AI for VLM

<div align="center">

![Python](https://img.shields.io/badge/python-3.12+-blue.svg?style=for-the-badge&logo=python&logoColor=white)
![Milvus](https://img.shields.io/badge/milvus-vector--db-pink.svg?style=for-the-badge)
![OpenAI](https://img.shields.io/badge/OpenAI-LLM-purple.svg?style=for-the-badge)

**Asistente Multimodal Educativo — Universidad Libre**

[Descripción](#-descripción) • [Instalación](#-instalación-y-setup) • [Arquitectura](#️-arquitectura) • [Documentación](#-documentación)

</div>

---

## 📋 Tabla de Contenidos

1. [ Descripción](#-descripción)
2. [✨ Características](#-características)
3. [ Arquitectura](#️-arquitectura)
4. [ Requisitos](#-requisitos)
5. [🚀 Instalación y Setup](#-instalación-y-setup)
6. [ Configuración de Entorno](#️-configuración-de-entorno)
7. [ Estructura del Proyecto](#-estructura-del-proyecto)
8. [ Documentación](#-documentación)
9. [ Seguridad](#-seguridad)
10. [ Estado del proyecto](#️-estado-del-proyecto)

---

##  Descripción

**PROMETEO** es un asistente multimodal (texto + visión) para el androide R-One, desarrollado para interactuar con la comunidad educativa de la Universidad Libre. El sistema resuelve dudas, proporciona información institucional y acompaña las interacciones con movimientos físicos coordinados.

El proyecto combina búsqueda semántica, una base vectorial de conocimiento y un modelo de lenguaje. Cuando encuentra una coincidencia relevante, recupera una respuesta previamente indexada; cuando no la encuentra, consulta el modelo de lenguaje y puede almacenar la nueva interacción.

---

## ✨ Características

- 🤖 **Identidad consistente**: androide R-One con tono cálido y formal.
- 🔍 **Búsqueda vectorial**: consulta conocimiento general y especializado mediante embeddings.
- 🧠 **RAG de recuperación directa**: recupera respuestas semánticamente similares desde Milvus y usa un LLM como fallback.
- 🔄 **Búsqueda híbrida**: combina búsqueda vectorial, coincidencia exacta y similitud de Jaccard.
- 🎙️ **Respuestas multimodales**: combina texto, contexto visual y movimientos/gestos coordinados.
- 🚫 **Filtro de lenguaje**: detecta y procesa palabras inapropiadas.
- 💾 **Memoria de interacciones**: mantiene separadas las respuestas verificadas y las respuestas generadas por el LLM.

---

##  Arquitectura

```text
Pregunta + contexto visual
            │
            ▼
Limpieza y detección de intención
            │
            ▼
Generación del embedding
            │
            ▼
Búsqueda en Milvus: conocimiento
            │
       ¿Hay coincidencia?
        ┌───┴───┐
       Sí       No
       │         │
       ▼         ▼
Respuesta   Búsqueda en interacciones
recuperada        │
                  ▼
             ¿Coincidencia exacta?
              ┌───┴───┐
             Sí       No
             │         │
             ▼         ▼
        Respuesta   Generación con LLM
        recuperada        │
                          ▼
                    Indexación opcional
```

El flujo principal se implementa en [`responder()`](utils/main.py:134):

1. Limpia la pregunta y detecta su intención.
2. Consulta la colección `conocimiento` mediante búsqueda vectorial.
3. Si no hay resultado, consulta `interacciones` con coincidencia exacta.
4. Si tampoco hay resultado, genera una respuesta con OpenAI.
5. Devuelve la respuesta y un movimiento válido.
6. Almacena la interacción generada cuando cumple las condiciones definidas.

> Este sistema es un RAG de recuperación directa: recupera respuestas finales almacenadas en lugar de recuperar fragmentos de documentos para pasarlos al LLM como contexto.

---

##  Requisitos

### Dependencias del Sistema

- 🐍 **Python 3.12 o superior**
- 📦 **uv** para gestionar el entorno y las dependencias
- 🗄️ **Milvus Lite**, instalado mediante `pymilvus`
- 🤖 **OpenAI API** para generar respuestas nuevas
- 💾 Memoria y espacio suficientes para descargar el modelo de embeddings

Las dependencias están declaradas en [`pyproject.toml`](pyproject.toml) y fijadas en [`uv.lock`](uv.lock).

---

## 🚀 Instalación y Setup

### 1. Clonar el Repositorio

```bash
git clone https://github.com/Semillero-Prometeo/pmai-model-vision-language.git
cd pmai-model-vision-language
```

### 2. Crear Entorno Virtual e Instalar Dependencias

```bash
uv sync
```

### 3. Activar el Entorno Virtual

**En Linux/macOS:**

```bash
source .venv/bin/activate
```

**En Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

### 4. Ejecutar el Proyecto

La lógica de respuesta se consume actualmente desde la integración principal del androide. Para probar la ingesta y la búsqueda de forma aislada, utiliza el notebook [`ingesta.ipynb`](utils/milvus/ingesta.ipynb) o importa [`responder()`](utils/main.py:134) desde un flujo de aplicación.

```python
from utils.main import responder

resultado = responder(objeto, movimientos)
print(resultado["respuesta"])
print(resultado["fuente"])  # "cache" o "llm"
```

---

##  Configuración de Entorno

Copia [`.env.example`](.env.example) como `.env` en la raíz del proyecto:

```bash
cp .env.example .env
```

Configura únicamente las credenciales necesarias:

```env
OPENAI_API_KEY=tu_clave_de_openai
```

No guardes claves reales en el repositorio. El archivo `.env` está excluido mediante [`.gitignore`](.gitignore).

Los parámetros principales se encuentran en [`utils/config.py`](utils/config.py):

- `OPENAI_MODEL`: modelo usado para generar respuestas.
- `EMBED_MODEL_NAME`: modelo usado para crear embeddings.
- `MILVUS_DB_PATH`: ubicación de la base vectorial local.
- `UMBRAL_CONOCIMIENTO` y `UMBRAL_INTERACCIONES`: umbrales de búsqueda.

---

##  Estructura del Proyecto

```text
pmai-model-vision-language/
├── data/
│   └── movimientos.json
├── docs/
├── models/
│   └── schemas.py
├── prompt/
│   ├── detector_grocerias.py
│   └── principal.py
├── utils/
│   ├── context_builder/
│   │   └── alimentar_basevec.py
│   ├── encoder/
│   │   └── encoder.py
│   ├── gpt/
│   │   └── gptapi.py
│   ├── milvus/
│   │   ├── busqueda.py
│   │   ├── conexion.py
│   │   ├── indexar.py
│   │   └── ingesta.ipynb
│   └── main.py
├── .env.example
├── pyproject.toml
├── README.md
└── uv.lock
```

---

## 📖 Documentación

### Flujo Principal

1. **Ingesta de datos**: carga preguntas y respuestas verificadas con [`alimentar_basevec()`](utils/context_builder/alimentar_basevec.py:16) o mediante [`ingesta.ipynb`](utils/milvus/ingesta.ipynb).
2. **Indexación**: genera embeddings y guarda los registros en la colección `conocimiento`.
3. **Búsqueda**: consulta la base vectorial con [`search()`](utils/milvus/busqueda.py:182).
4. **Generación**: construye el prompt y genera respuestas con [`generar_respuesta()`](utils/gpt/gptapi.py:98).
5. **Filtrado**: detecta contenido inapropiado y valida los movimientos.
6. **Memoria**: almacena interacciones válidas en la colección `interacciones`.

### Recursos Útiles

- Notebook de ingesta: [`ingesta.ipynb`](utils/milvus/ingesta.ipynb)
- Configuración de Milvus: [`conexion.py`](utils/milvus/conexion.py)
- Búsqueda semántica: [`busqueda.py`](utils/milvus/busqueda.py)
- Indexación: [`indexar.py`](utils/milvus/indexar.py)
- Construcción del prompt: [`principal.py`](prompt/principal.py)
- Detector de groserías: [`detector_grocerias.py`](prompt/detector_grocerias.py)

---

##  Seguridad

- Usa variables de entorno para las claves y no las incluyas en el código.
- No registres tokens, claves, datos personales ni el contenido completo de solicitudes sensibles.
- Revisa las respuestas generadas antes de utilizarlas en un entorno educativo.
- Valida los datos de entrada y los movimientos antes de indexarlos o ejecutarlos.
- Mantén las dependencias actualizadas y ejecuta análisis de vulnerabilidades antes de desplegar.

---

##  Estado del proyecto

Este repositorio está en desarrollo; algunos módulos son experimentales. Antes de un uso productivo se recomienda:

- Medir precisión, recall, latencia y tasa de respuestas correctas.
- Validar los umbrales de búsqueda con un conjunto de evaluación real.
- Revisar las respuestas generadas antes de incorporarlas a la memoria de interacciones.
- Completar las pruebas de integración con visión, voz, movimiento y el lanzador del androide.
- Completar la documentación de despliegue y operación.

La ingesta de conocimiento debe revisarse antes de indexar información institucional.

---

##  Contacto y Autor

**Equipo PROMETEO — Universidad Libre**

Si encuentras un error o quieres colaborar, abre un issue o contacta al responsable del proyecto.

---

##  Licencia

Consulta [`LICENSE`](LICENSE) para conocer las condiciones de uso y distribución.
