import importlib


def test_package_imports() -> None:
    module = importlib.import_module("cellar")
    assert module is not None
