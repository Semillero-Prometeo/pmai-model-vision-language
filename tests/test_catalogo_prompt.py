from prompt.principal import construir_prompt, formatear_catalogo


class Obj:
    etiqueta = "Andrea"
    contexto = "persona de frente"


def test_empty_catalog_is_explicit():
    assert formatear_catalogo([]) == "(No hay movimientos disponibles)"


def test_catalog_is_a_markdown_table_with_blank_description():
    table = formatear_catalogo(
        [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}]
    )
    assert "| id | nombre | arduino_id | descripcion |" in table
    assert "| 4 | Saludo | 1 |  |" in table


def test_prompt_has_no_fixed_gesture_ids():
    prompt = construir_prompt(Obj(), "Hola", [{"id": 4, "name": "Saludo", "arduino_id": 1, "description": ""}])
    assert "Saludo brazo derecho" not in prompt
    assert "· 33" not in prompt
    assert "· 34" not in prompt
    assert "| 4 | Saludo | 1 |  |" in prompt
