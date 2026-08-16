import urllib.parse
from unittest.mock import patch

from cellar.schemas.sources import StringPartner
from cellar.services.sources import string_db


def test_get_json_returns_list_from_http() -> None:
    with patch.object(string_db.http, "get_json", return_value=[{"a": 1}]):
        assert string_db._get_json("http://x") == [{"a": 1}]


def test_string_partners_calls_http_get_json_with_expected_url() -> None:
    with patch.object(string_db.http, "get_json", return_value=[]) as mock_get_json:
        string_db.string_partners("ZDHHC20")

    qs = urllib.parse.urlencode({"identifiers": "ZDHHC20", "species": 9606, "limit": 15})
    mock_get_json.assert_called_once_with(
        f"{string_db.STRING_URL}/interaction_partners?{qs}",
        headers={"Accept": "application/json"},
        timeout=40,
    )


def test_string_partners_returns_typed_partners_above_min_score() -> None:
    payload = [
        {"preferredName_B": "ZDHHC5", "score": 0.912345},
        {"preferredName_B": "LOW", "score": 0.1},
    ]
    with patch.object(string_db.http, "get_json", return_value=payload):
        result = string_db.string_partners("ZDHHC20")

    assert result == [StringPartner(partner="ZDHHC5", score=0.912)]
