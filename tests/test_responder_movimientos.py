import utils.main as main_module
from models.schemas import GlobalObjectForContext


def test_responder_keeps_three_catalog_ids_and_drops_unknown(monkeypatch):
    monkeypatch.setattr(main_module, "search", lambda *args, **kwargs: {"hit": False})
    monkeypatch.setattr(
        main_module,
        "generar_respuesta",
        lambda prompt: {"respuesta": "Hola", "movimientos": [4, 99, 2, 7, 8], "_backend": "gguf"},
    )
    monkeypatch.setattr(main_module, "indexar", lambda *args, **kwargs: None)
    obj = GlobalObjectForContext(id_global="g", etiqueta="Andrea", confianza=0.9, question="Hola")
    catalogo = [
        {"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""},
        {"id": 2, "name": "Asentir", "arduino_id": 1, "description": ""},
        {"id": 7, "name": "Pecho", "arduino_id": 1, "description": ""},
        {"id": 8, "name": "Hombros", "arduino_id": 1, "description": ""},
    ]
    salida = main_module.responder(obj, catalogo)
    assert salida["movimientos"] == [4, 2, 7]
    assert salida["respuesta"] == "Hola"
    assert salida["fuente"] == "llm"


def test_search_failure_falls_through_to_the_model(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("milvus down")

    monkeypatch.setattr(main_module, "search", boom)
    monkeypatch.setattr(
        main_module,
        "generar_respuesta",
        lambda prompt: {"respuesta": "Desde el modelo", "movimientos": [], "_backend": "gguf"},
    )
    indexed = {"called": False}

    def no_index(*args, **kwargs):
        indexed["called"] = True

    monkeypatch.setattr(main_module, "indexar", no_index)
    obj = GlobalObjectForContext(id_global="g", etiqueta="Andrea", confianza=0.9, question="dato")
    salida = main_module.responder(obj, [])
    assert salida["respuesta"] == "Desde el modelo"
    assert indexed["called"] is False
