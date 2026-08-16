import json
from unittest.mock import mock_open, patch

from cellar.services.sources import cell_model_passports


def test_fetch_cache_hit_skips_network() -> None:
    cached_payload = {"data": {"id": "1"}}
    with (
        patch.object(cell_model_passports.os.path, "exists", return_value=True),
        patch("builtins.open", mock_open(read_data=json.dumps(cached_payload))),
        patch.object(cell_model_passports.http, "get_json") as mock_get_json,
    ):
        result = cell_model_passports._fetch("http://x")

    assert result == cached_payload
    mock_get_json.assert_not_called()


def test_fetch_cache_miss_calls_http_get_json_and_writes_cache(tmp_path: object) -> None:
    payload = {"data": {"id": "2"}}
    cache_dir = str(tmp_path)

    with patch.object(cell_model_passports.http, "get_json", return_value=payload) as mock_get_json:
        result = cell_model_passports._fetch("http://x", cache_dir=cache_dir)

    assert result == payload
    (called_url,), called_kwargs = mock_get_json.call_args
    assert called_url == "http://x"
    assert called_kwargs == {"headers": cell_model_passports._HEADERS, "timeout": 60}

    cache_path = cell_model_passports._cache_file("http://x", cache_dir)
    with open(cache_path) as f:
        assert json.load(f) == payload
