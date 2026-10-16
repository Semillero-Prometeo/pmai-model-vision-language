from pathlib import Path

import utils.gpt.gptapi as gpt


def test_key_uses_openai_even_if_dns_probe_would_fail(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(gpt, "hay_internet", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        gpt,
        "llamar_openai",
        lambda prompt: {"respuesta": "hola", "movimientos": []},
    )
    monkeypatch.setattr(
        gpt,
        "_generar_respuesta_gguf",
        lambda prompt: (_ for _ in ()).throw(AssertionError("gguf must not run")),
    )
    out = gpt.generar_respuesta("pregunta")
    assert out["_backend"] == "openai"
    assert out["respuesta"] == "hola"


def test_openai_failure_falls_back_to_gguf(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    def boom(prompt):
        raise RuntimeError("401")

    monkeypatch.setattr(gpt, "llamar_openai", boom)
    monkeypatch.setattr(
        gpt,
        "_generar_respuesta_gguf",
        lambda prompt: {"respuesta": "local", "movimientos": []},
    )
    out = gpt.generar_respuesta("pregunta")
    assert out["_backend"] == "gguf"
    assert out["respuesta"] == "local"


def test_missing_key_does_not_call_openai(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    called = []
    monkeypatch.setattr(gpt, "llamar_openai", lambda prompt: called.append(prompt) or {})
    monkeypatch.setattr(
        gpt,
        "_generar_respuesta_gguf",
        lambda prompt: {"respuesta": "local", "movimientos": []},
    )
    out = gpt.generar_respuesta("pregunta")
    assert called == []
    assert out["_backend"] == "gguf"


def test_empty_key_does_not_call_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    called = []
    monkeypatch.setattr(gpt, "llamar_openai", lambda prompt: called.append(prompt) or {})
    monkeypatch.setattr(
        gpt,
        "_generar_respuesta_gguf",
        lambda prompt: {"respuesta": "local", "movimientos": []},
    )
    out = gpt.generar_respuesta("pregunta")
    assert called == []
    assert out["_backend"] == "gguf"


def test_generar_respuesta_source_does_not_gate_on_hay_internet():
    text = Path("utils/gpt/gptapi.py").read_text(encoding="utf-8")
    router = text.split("def generar_respuesta")[1].split("def ")[0]
    assert "hay_internet" not in router
    assert "8.8.8.8" not in text


def test_load_dotenv_does_not_override_existing_env():
    text = Path("utils/config.py").read_text(encoding="utf-8")
    assert "load_dotenv" in text
    assert "override=True" not in text
    assert "override=False" in text
