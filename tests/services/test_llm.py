from pathlib import Path

import pytest

from cellar.config import ModelProvider, Settings
from cellar.services.llm import has_api_key, needs_api_key, write_api_key_to_env


def test_write_api_key_to_env_appends_when_absent(tmp_path: Path) -> None:
    path = tmp_path / ".env"

    write_api_key_to_env("sk-ant-new", path)

    assert path.read_text() == "ANTHROPIC_API_KEY=sk-ant-new\n"


def test_write_api_key_to_env_replaces_existing_line(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("OTHER_VAR=keep\nANTHROPIC_API_KEY=oldval\nAFTER_VAR=also-keep\n")

    write_api_key_to_env("sk-ant-new", path)

    assert path.read_text() == "OTHER_VAR=keep\nANTHROPIC_API_KEY=sk-ant-new\nAFTER_VAR=also-keep\n"


def test_write_api_key_to_env_replaces_empty_value(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("ANTHROPIC_API_KEY=\n")

    write_api_key_to_env("sk-ant-new", path)

    assert path.read_text() == "ANTHROPIC_API_KEY=sk-ant-new\n"


def test_has_api_key_true_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-set")

    assert has_api_key() is True


def test_has_api_key_false_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert has_api_key() is False


def test_has_api_key_false_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

    assert has_api_key() is False


def test_needs_api_key_true_for_direct_api_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings = Settings(provider=ModelProvider.DIRECT_API)

    assert needs_api_key(settings) is True


def test_needs_api_key_true_for_direct_api_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    settings = Settings(provider=ModelProvider.DIRECT_API)

    assert needs_api_key(settings) is True


def test_needs_api_key_false_for_direct_api_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-set")
    settings = Settings(provider=ModelProvider.DIRECT_API)

    assert needs_api_key(settings) is False


def test_needs_api_key_false_for_bedrock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings = Settings(provider=ModelProvider.BEDROCK)

    assert needs_api_key(settings) is False
