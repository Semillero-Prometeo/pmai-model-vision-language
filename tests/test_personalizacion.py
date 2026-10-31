import sys

import numpy as np

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
