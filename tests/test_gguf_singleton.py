import utils.gguf.ggufapi as gguf


class FakeLlama:
    def __init__(self):
        self.resets = 0
        self.texts = [""]

    def reset(self):
        self.resets += 1

    def __call__(self, prompt, max_tokens, stop, **params):
        text = (
            self.texts.pop(0) if self.texts else '{"respuesta":"ok","movimientos":[]}'
        )
        return {"choices": [{"text": text}]}


def test_asegurar_modelo_downloads_only_when_missing(tmp_path, monkeypatch):
    dest = tmp_path / "gemma-4-E2B-it-Q4_K_M.gguf"
    monkeypatch.setattr(gguf, "GGUF_MODEL_PATH", str(dest))
    calls = []

    def fake_download(repo_id, filename, local_dir):
        calls.append((repo_id, filename, local_dir))
        (tmp_path / filename).write_bytes(b"gguf")
        return str(tmp_path / filename)

    monkeypatch.setattr(gguf, "_descargar_gguf", fake_download)
    gguf.asegurar_modelo()
    gguf.asegurar_modelo()

    assert dest.is_file()
    assert calls == [
        ("unsloth/gemma-4-E2B-it-GGUF", "gemma-4-E2B-it-Q4_K_M.gguf", str(tmp_path))
    ]


def test_empty_generation_rebuilds_once(monkeypatch):
    created = []

    def factory():
        llama = FakeLlama()
        if not created:
            llama.texts = [""]
        else:
            llama.texts = ['{"respuesta":"ok","movimientos":[1]}']
        created.append(llama)
        return llama

    monkeypatch.setattr(gguf, "_LLAMA_DISPONIBLE", True)
    monkeypatch.setattr(gguf, "_nueva_instancia", factory)
    monkeypatch.setattr(gguf, "asegurar_modelo", lambda: None)
    gguf._llm = None
    salida = gguf.llamar_gguf("pregunta")
    assert salida["respuesta"] == "ok"
    assert len(created) == 2
    assert created[0].resets == 1
