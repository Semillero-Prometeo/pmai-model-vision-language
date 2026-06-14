# pmai-model-vision-language
PROMETEO — Multimodal AI for VLM
#https://gist.github.com/rxaviers/7360908

<div align="center">

![Python](https://img.shields.io/badge/python-3.13+-blue.svg?style=for-the-badge&logo=python&logoColor=white)
![Milvus](https://img.shields.io/badge/milvus-vector--db-pink.svg?style=for-the-badge)
![Ollama](https://img.shields.io/badge/ollama-local--llm-purple.svg?style=for-the-badge)

**Asistente Multimodal Educativo — Universidad Libre**

[Descripción](#-descripción) • [Instalación](#-instalación-y-setup) • [Documentación](#-documentación)

</div>

---

## 📋 Tabla de Contenidos

1. [🎯 Descripción](#-descripción)
2. [✨ Características](#-características)
3. [🏗️ Arquitectura](#️-arquitectura)
4. [📦 Requisitos](#-requisitos)
5. [🚀 Instalación y Setup](#-instalación-y-setup)
6. [⚙️ Configuración de Entorno](#️-configuración-de-entorno)
7. [📂 Estructura del Proyecto](#-estructura-del-proyecto)
8. [📖 Documentación](#-documentación)

---

## 🎯 Descripción

**PROMETEO** es un asistente multimodal (texto + visión) un lindo robot en desarrollo para interactuar con la comunidad educativa de la Universidad Libre. Funciona como un androide que resuelve dudas, proporciona información institucional y acompaña interacciones en entornos educativos.

---

## ✨ Características

- 🤖 **Identidad consistente**: androide R-One con tono calido y formal bien bello
- 🔍 **Busqueda vectorial**: base de datos de conocimiento general y especializado 
- 🎙️ **Respuestas multimodales**: texto + movimientos/gestos coordinados idk como
- 🚫 **Filtro de lenguaje**: detección y censura de palabras inapropiadas que ya ta
- 💾 **Archivos vectoriales**: colecciones Milvus para consultas rápidas tm ya ta tenemos

---

## 🏗️ Arq

```
añadirla en algun momentos
```

---

## 📦 Requisitos

### Dependencias del Sistema

- 🐍 **Python** 
- 🐳 **Milvus**
- 📦 **uv** gestor de paquetes
- 🦙 **Ollama** (opcional) para LLM local mas linda la llama
- 🤖 **GPT** El de la u

---

## 🚀 Instalación y Setup

### 1. Clonar el Repositorio

```bash
git https://github.com/Semillero-Prometeo/pmai-model-vision-language.git
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

**En Windows (PowerShell):**

```powershell
busca

```


### 4. Ejecutar el Proyecto

```bash

idk

```

---

## ⚙️ Configuración de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
```

---

## 📂 Estructura del Proyecto

```
pmai-model-vision-language/
├── main.py                          
├── main.ipynb                      
├── pyproject.toml                   
├── .env                            
├── prompt/
│   ├── principal.py                 
│   ├── detector_grocerias.py        
│   └── __init__.py
├── models/
│   ├── schemas.py                   
│   └── __init__.py
├── utils/
│   ├── config.py                    
│   ├── context_builder/             
│   │   ├── limpieza.py
│   │   ├── alimentar_basevec.py
│   │   └── __init__.py
│   ├── encoder/                     
│   │   ├── encoder.py
│   │   └── __init__.py
│   ├── milvus/                      
│   │   ├── conexion.py
│   │   ├── busqueda.py
│   │   ├── ingesta.ipynb
│   │   └── __init__.py
│   ├── searcher/                    
│   │   └── __init__.py
│   ├── ollama/                      
│   │   └── __init__.py
│   ├── gpt/                         
│   │   └── __init__.py
│   └── webscraping/                 
├── data/
│   ├── preguntas.txt                
│   └── movimientos.ts               
└── docs/                           
```

---

## 📖 Documentación

### Flujo Principal

1. **Ingesta de datos**: carga documentos en `utils/milvus/ingesta.ipynb`
2. **Busqueda**: consulta la base vectorial con `utils/milvus/busqueda.py`
3. **Generación**: crea respuestas con `prompt/principal.py`
4. **Filtrado**: detecta y censura lenguaje inapropiado

### Recursos Útiles

- Notebook de ingesta: [ingesta.ipynb](utils/milvus/ingesta.ipynb)
- Configuración de Milvus: [conexion.py](utils/milvus/conexion.py)
- Detector de groserias: [detector_grocerias.py](prompt/detector_grocerias.py)

---

## ⚠️ Notas Importantes

- Este repositorio esta en desarrollo; algunos modulos son experimentales osea todos.
- La ingesta de datos requiere verificación manual antes de indexar (no tocar :).
- Si usas herramientas de IA para generar textos o datos documentalo en los commits.
- El prompt toca mejorarlo con IA

---

## 👥 Contacto y Autor

**Equipo PROMETEO — Universidad Libre**  
Si quieres colaborar encontraste un error o necesitas ayudaabre un issue o contacta al responsable del proyecto.

---

## 📄 Licencia

Consulta [LICENSE](LICENSE) para detalles sobre uso y distribución.





