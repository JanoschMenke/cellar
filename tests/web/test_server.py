import os
from pathlib import Path
from typing import Any

import httpx
import pytest
from anthropic import AuthenticationError
from fastapi.testclient import TestClient

import cellar.web.server as server
from cellar.agents.streaming_agent import StreamingAgent


class _FakeModels:
    def __init__(self, should_reject: bool) -> None:
        self._should_reject = should_reject

    def list(self, limit: int) -> None:
        if self._should_reject:
            response = httpx.Response(
                status_code=401, request=httpx.Request("GET", "https://api.anthropic.com/v1/models")
            )
            raise AuthenticationError("invalid x-api-key", response=response, body=None)


class _FakeClient:
    def __init__(self, api_key: str | None, should_reject: bool = False) -> None:
        self.api_key = api_key
        self.models = _FakeModels(should_reject)


@pytest.fixture
def rejecting_keys() -> set[str]:
    return {"sk-ant-rejected"}


@pytest.fixture
def client_app(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, rejecting_keys: set[str]
) -> tuple[TestClient, Path, list[Any]]:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("CELLAR_PROVIDER", "direct_api")

    def fake_build_client(settings: Any, api_key: str | None = None) -> _FakeClient:
        return _FakeClient(api_key, should_reject=api_key in rejecting_keys)

    monkeypatch.setattr(server, "build_client", fake_build_client)

    set_client_calls: list[Any] = []
    original_set_client = StreamingAgent.set_client

    def tracking_set_client(self: StreamingAgent, client: Any) -> None:
        set_client_calls.append(client)
        original_set_client(self, client)

    monkeypatch.setattr(StreamingAgent, "set_client", tracking_set_client)

    env_path = tmp_path / ".env"
    monkeypatch.setattr(server, "_ENV_PATH", env_path)

    app = server.create_app()
    return TestClient(app), env_path, set_client_calls


def test_config_reports_needs_api_key_when_unset(
    client_app: tuple[TestClient, Path, list[Any]],
) -> None:
    client, _, _ = client_app

    response = client.get("/config")

    assert response.status_code == 200
    body = response.json()
    assert body["needs_api_key"] is True


def test_post_api_key_valid_key_applies_and_persists(
    client_app: tuple[TestClient, Path, list[Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, env_path, set_client_calls = client_app

    response = client.post("/api-key", json={"api_key": "sk-ant-good"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-ant-good"
    assert env_path.exists()
    assert env_path.read_text().strip() == "ANTHROPIC_API_KEY=sk-ant-good"
    assert len(set_client_calls) == 1
    assert set_client_calls[0].api_key == "sk-ant-good"

    config_response = client.get("/config")
    assert config_response.json()["needs_api_key"] is False


def test_post_api_key_rejected_by_anthropic_leaves_state_unchanged(
    client_app: tuple[TestClient, Path, list[Any]],
) -> None:
    client, env_path, set_client_calls = client_app

    response = client.post("/api-key", json={"api_key": "sk-ant-rejected"})

    assert response.status_code == 401
    body = response.json()
    assert body["ok"] is False
    assert "rejected" in body["error"]
    assert "ANTHROPIC_API_KEY" not in os.environ
    assert not env_path.exists()
    assert set_client_calls == []


def test_post_api_key_without_expected_prefix_is_rejected(
    client_app: tuple[TestClient, Path, list[Any]],
) -> None:
    client, env_path, set_client_calls = client_app

    response = client.post("/api-key", json={"api_key": "not-a-key"})

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert "ANTHROPIC_API_KEY" not in os.environ
    assert not env_path.exists()
    assert set_client_calls == []
