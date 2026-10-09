import utils.gguf.ggufapi as gguf


class FakeLlama:
    def __init__(self):
        self.resets = 0
        self.texts = [""]

    def reset(self):
        self.resets += 1

    def __call__(self, prompt, max_tokens, stop, **params):
        text = self.texts.pop(0) if self.texts else '{"respuesta":"ok","movimientos":[]}'
        return {"choices": [{"text": text}]}


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
    monkeypatch.setattr(gguf.os.path, "isfile", lambda path: True)
    gguf._llm = None
    salida = gguf.llamar_gguf("pregunta")
    assert salida["respuesta"] == "ok"
    assert len(created) == 2
    assert created[0].resets == 1
