import json
from unittest.mock import patch

import pytest

from cellar.utils import http


class _FakeResp:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_get_bytes_returns_raw() -> None:
    with patch.object(http.urllib.request, "urlopen", return_value=_FakeResp(b"<xml/>")):
        assert http.get_bytes("http://x") == b"<xml/>"


def test_get_json_parses_dict_and_list() -> None:
    with patch.object(
        http.urllib.request, "urlopen", return_value=_FakeResp(json.dumps({"a": 1}).encode())
    ):
        assert http.get_json("http://x") == {"a": 1}
    with patch.object(
        http.urllib.request, "urlopen", return_value=_FakeResp(json.dumps([1, 2]).encode())
    ):
        assert http.get_json("http://x") == [1, 2]


def test_post_json_sends_body_and_content_type() -> None:
    captured: dict[str, object] = {}

    def _fake_urlopen(request: object, timeout: int = 0) -> _FakeResp:
        captured["data"] = request.data  # type: ignore[attr-defined]
        captured["ct"] = request.headers.get("Content-type")  # type: ignore[attr-defined]
        return _FakeResp(json.dumps({"ok": True}).encode())

    with patch.object(http.urllib.request, "urlopen", _fake_urlopen):
        result = http.post_json("http://x", {"q": 1})
    assert result == {"ok": True}
    assert json.loads(captured["data"]) == {"q": 1}
    assert captured["ct"] == "application/json"


def test_http_error_carries_status_and_body() -> None:
    import urllib.error

    def _raise(*a: object, **k: object) -> None:
        raise urllib.error.HTTPError("http://x", 404, "nope", {}, io_body())

    with (
        patch.object(http.urllib.request, "urlopen", _raise),
        pytest.raises(http.HttpError) as excinfo,
    ):
        http.get_json("http://x")
    assert excinfo.value.status == 404
    assert "not found body" in excinfo.value.body


def io_body():
    import io

    return io.BytesIO(b"not found body")
