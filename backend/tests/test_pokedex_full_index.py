from app.services.data_loader import load_pokemon_index


def test_pokemon_index_supports_national_dex_ids_beyond_999():
    pokemon_index = load_pokemon_index()

    assert any(entry['id'] == '1000' for entry in pokemon_index)
