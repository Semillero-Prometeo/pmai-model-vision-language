"""Avoid loading SentenceTransformer (and downloading weights) when importing utils.main."""
import sys
from unittest.mock import MagicMock

sys.modules.setdefault("sentence_transformers", MagicMock())
sys.modules.setdefault("openai", MagicMock())
sys.modules.setdefault("pymilvus", MagicMock())


class _IdentityPalabrota:
    def contains_palabrota(self, text):
        return False

    def censor(self, text):
        return text


_spanlp_palabrota = MagicMock()
_spanlp_palabrota.Palabrota = _IdentityPalabrota
sys.modules.setdefault("spanlp", MagicMock())
sys.modules.setdefault("spanlp.palabrota", _spanlp_palabrota)

_encoder = MagicMock()
_encoder.embed = lambda texto: [0.0] * 8
sys.modules["utils.encoder.encoder"] = _encoder
