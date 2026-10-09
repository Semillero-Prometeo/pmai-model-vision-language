"""Avoid loading SentenceTransformer (and downloading weights) when importing utils.main."""
import sys
from unittest.mock import MagicMock

sys.modules.setdefault("sentence_transformers", MagicMock())

_encoder = MagicMock()
_encoder.embed = lambda texto: [0.0] * 8
sys.modules["utils.encoder.encoder"] = _encoder
