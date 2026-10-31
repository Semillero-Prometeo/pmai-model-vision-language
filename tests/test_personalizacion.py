import sys

import numpy as np

import utils.main as main_module
import utils.personalizacion as pers
from models.schemas import GlobalObjectForContext


def _patch_embed(monkeypatch, fn):
    monkeypatch.setattr(sys.modules["utils.encoder.encoder"], "embed", fn)


def _reset_situaciones(monkeypatch, vectores, aperturas=("veo que buscas orientacion",)):
    matriz = np.array(vectores, dtype=np.float32)
    monkeypatch.setattr(
        pers,
        "_SITUACIONES",
        [("confusion_orientacion", list(aperturas), matriz)],
    )


def test_elegir_apertura_empty_context_is_none():
    assert pers.elegir_apertura("") is None
    assert pers.elegir_apertura(None) is None


def test_elegir_apertura_above_threshold(monkeypatch):
    unit = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    _reset_situaciones(monkeypatch, [unit])
    monkeypatch.setattr(pers, "UMBRAL_APERTURA", 0.60)

    def fake_embed(texto):
        return unit

    _patch_embed(monkeypatch, fake_embed)
    assert pers.elegir_apertura("person looking at a map") == "veo que buscas orientacion"


def test_elegir_apertura_below_threshold(monkeypatch):
    unit = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    ortho = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    _reset_situaciones(monkeypatch, [unit])
    monkeypatch.setattr(pers, "UMBRAL_APERTURA", 0.60)
    _patch_embed(monkeypatch, lambda texto: ortho)
    assert pers.elegir_apertura("unrelated blur") is None


def test_elegir_apertura_embed_failure_is_none(monkeypatch):
    _reset_situaciones(monkeypatch, [[1.0] * 8])

    def boom(texto):
        raise RuntimeError("encoder down")

    _patch_embed(monkeypatch, boom)
    assert pers.elegir_apertura("person smiling") is None


def test_etiqueta_real_keeps_a_name():
    assert main_module._etiqueta_real("Andrea") == "Andrea"
    assert main_module._etiqueta_real("  Pedro  ") == "Pedro"


def test_etiqueta_real_drops_placeholder():
    assert main_module._etiqueta_real("Persona no identificada") == ""
    assert main_module._etiqueta_real("") == ""
    assert main_module._etiqueta_real(None) == ""
    assert main_module._etiqueta_real("(sin nombre)") == ""


def test_limpiar_sin_nombre_strips_prefix():
    assert (
        main_module._limpiar_sin_nombre("Persona no identificada, el semillero Prometeo.")
        == "El semillero Prometeo."
    )


def test_anteponer_nombre_with_and_without_apertura():
    assert (
        main_module._anteponer_nombre("Andrea", "El semillero Prometeo.")
        == "Andrea, el semillero Prometeo."
    )
    assert (
        main_module._anteponer_nombre(
            "Andrea",
            "El semillero Prometeo.",
            "veo que buscas orientacion",
        )
        == "Andrea, veo que buscas orientacion. El semillero Prometeo."
    )
    assert (
        main_module._anteponer_nombre(
            "",
            "El semillero Prometeo.",
            "veo que buscas orientacion",
        )
        == "Veo que buscas orientacion. El semillero Prometeo."
    )
    assert main_module._anteponer_nombre("", "El semillero Prometeo.") == "El semillero Prometeo."


def test_anteponer_nombre_keeps_sigla_and_r_one():
    assert main_module._anteponer_nombre("Andrea", "R-One está listo.") == "Andrea, R-One está listo."
    assert main_module._anteponer_nombre("Andrea", "UNAL tiene sede aquí.") == "Andrea, UNAL tiene sede aquí."


def test_quitar_nombre_strips_prefix_and_skips_embedded():
    assert (
        main_module._quitar_nombre("Andrea, el semillero Prometeo.", "Andrea")
        == "El semillero Prometeo."
    )
    assert main_module._quitar_nombre("Hola Andrea, ¿cómo estás?", "Andrea") is None
    assert (
        main_module._quitar_nombre("El semillero Prometeo.", "Persona no identificada")
        == "El semillero Prometeo."
    )


def _hit(respuesta="El semillero Prometeo.", movimientos=None):
    return {
        "hit": True,
        "data": {"respuesta": respuesta, "movimientos": movimientos if movimientos is not None else [4]},
    }


def test_cache_unidentified_does_not_speak_placeholder(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *args, **kwargs: _hit("El semillero Prometeo."))
    monkeypatch.setattr(main_module, "elegir_apertura", lambda contexto: None)
    monkeypatch.setattr(
        main_module,
        "generar_respuesta",
        lambda prompt: (_ for _ in ()).throw(AssertionError("llm must not run")),
    )
    obj = GlobalObjectForContext(
        id_global="g",
        etiqueta="Persona no identificada",
        confianza=0.1,
        question="¿Qué es Prometeo?",
    )
    catalogo = [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}]
    salida = main_module.responder(obj, catalogo)
    assert "Persona no identificada" not in salida["respuesta"]
    assert salida["respuesta"] == "El semillero Prometeo."
    assert salida["movimientos"] == [4]
    assert salida["fuente"] == "cache"
    assert salida["etiqueta"] == ""


def test_cache_name_without_apertura(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *args, **kwargs: _hit("El semillero Prometeo."))
    monkeypatch.setattr(main_module, "elegir_apertura", lambda contexto: None)
    obj = GlobalObjectForContext(id_global="g", etiqueta="Andrea", confianza=0.9, question="dato")
    salida = main_module.responder(obj, [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}])
    assert salida["respuesta"].startswith("Andrea, ")
    assert "El semillero Prometeo." in salida["respuesta"] or "el semillero Prometeo." in salida["respuesta"]


def test_cache_name_with_apertura(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *args, **kwargs: _hit("El semillero Prometeo."))
    monkeypatch.setattr(main_module, "elegir_apertura", lambda contexto: "veo que buscas orientacion")
    obj = GlobalObjectForContext(
        id_global="g",
        etiqueta="Andrea",
        confianza=0.9,
        question="dato",
        contexto="person looking at a map",
    )
    salida = main_module.responder(obj, [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}])
    assert salida["respuesta"] == "Andrea, veo que buscas orientacion. El semillero Prometeo."


def test_cache_apertura_without_name(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *args, **kwargs: _hit("El semillero Prometeo."))
    monkeypatch.setattr(main_module, "elegir_apertura", lambda contexto: "veo que buscas orientacion")
    obj = GlobalObjectForContext(
        id_global="g",
        etiqueta="Persona no identificada",
        confianza=0.1,
        question="dato",
        contexto="person looking at a map",
    )
    salida = main_module.responder(obj, [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}])
    assert salida["respuesta"] == "Veo que buscas orientacion. El semillero Prometeo."


def test_llm_strips_placeholder_and_does_not_index_name(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *args, **kwargs: {"hit": False})
    monkeypatch.setattr(
        main_module,
        "generar_respuesta",
        lambda prompt: {
            "respuesta": "Andrea, el semillero Prometeo.",
            "movimientos": [4],
            "_backend": "gguf",
        },
    )
    captured = {}

    def fake_indexar(pregunta, respuesta, movimientos, collection_name=None):
        captured["respuesta"] = respuesta
        captured["movimientos"] = movimientos

    monkeypatch.setattr(main_module, "indexar", fake_indexar)
    obj = GlobalObjectForContext(id_global="g", etiqueta="Andrea", confianza=0.9, question="info sobre prometeo")
    salida = main_module.responder(obj, [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}])
    assert salida["respuesta"] == "Andrea, el semillero Prometeo."
    assert salida["movimientos"] == [4]
    assert salida["fuente"] == "llm"
    assert captured["respuesta"] == "El semillero Prometeo."


def test_llm_skips_index_when_name_cannot_be_stripped(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *args, **kwargs: {"hit": False})
    monkeypatch.setattr(
        main_module,
        "generar_respuesta",
        lambda prompt: {
            "respuesta": "Hola Andrea, el semillero Prometeo te espera.",
            "movimientos": [4],
            "_backend": "gguf",
        },
    )
    indexed = {"called": False}

    def no_index(*args, **kwargs):
        indexed["called"] = True

    monkeypatch.setattr(main_module, "indexar", no_index)
    obj = GlobalObjectForContext(id_global="g", etiqueta="Andrea", confianza=0.9, question="info sobre prometeo")
    salida = main_module.responder(obj, [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}])
    assert "Andrea" in salida["respuesta"]
    assert indexed["called"] is False


def test_llm_unidentified_placeholder_is_stripped(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *args, **kwargs: {"hit": False})
    monkeypatch.setattr(
        main_module,
        "generar_respuesta",
        lambda prompt: {
            "respuesta": "Persona no identificada, el semillero Prometeo.",
            "movimientos": [],
            "_backend": "gguf",
        },
    )
    monkeypatch.setattr(main_module, "indexar", lambda *args, **kwargs: None)
    obj = GlobalObjectForContext(
        id_global="g",
        etiqueta="Persona no identificada",
        confianza=0.1,
        question="info",
    )
    salida = main_module.responder(obj, [])
    assert salida["respuesta"] == "El semillero Prometeo."
    assert "Persona no identificada" not in salida["respuesta"]
