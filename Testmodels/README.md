<!-- markdownlint-disable MD012 -->

# Test Time Models

```bash
cd Testmodels

```

## Instalar UV

comandos utiles

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv init 
uv add dependecie
uv remove dependecie
uv sync
uv tree
uv run 
```



## Guide

#### 3. Create Virtual Environment and install dependencies

Use uv to create the virtual environment:

```bash
uv sync
```

**Activate the virtual environment:**
**On Linux/macOS:**


```bash
.source .venv/bin/activate
```


**On Windows (PowerShell):**

```bash
.\.venv\Scripts\Activate.ps1
```


## Jupyter

```bash
python -m ipykernel install --user --name=.venv
jupyter lab

```

### logearte con el server de jupyter en el kernel




## Guide to the local models

