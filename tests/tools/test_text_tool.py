from cellar.tools.text import CountCharactersTool


def test_count_characters_valid() -> None:
    assert CountCharactersTool().dispatch({"text": "hello"}).content == "5"


def test_count_characters_missing_required() -> None:
    assert CountCharactersTool().dispatch({}).is_error is True
