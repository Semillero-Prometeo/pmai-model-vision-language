import utils.milvus.conexion as conexion
from utils.config import COL_CONOCIMIENTO, COL_INTERACCIONES


def test_startup_creates_both_collections(tmp_path, monkeypatch):
    db = tmp_path / "androide_milvus.db"
    monkeypatch.setattr(conexion, "MILVUS_DB_PATH", str(db))
    conexion.reiniciar_cliente()
    client = conexion.get_client()
    assert client.has_collection(COL_CONOCIMIENTO)
    assert client.has_collection(COL_INTERACCIONES)
