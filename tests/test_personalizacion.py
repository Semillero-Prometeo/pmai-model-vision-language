import sys

import numpy as np

import utils.main as main_module
import utils.personalizacion as pers


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
