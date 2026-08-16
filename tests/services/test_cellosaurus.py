import urllib.parse
from unittest.mock import patch

from cellar.schemas.sources import CellModelHit
from cellar.services.sources import cellosaurus

_FAKE_PAYLOAD: dict[str, object] = {
    "Cellosaurus": {
        "cell-line-list": [
            {
                "accession-list": [{"type": "primary", "value": "CVCL_0001"}],
                "name-list": [{"value": "HeLa"}],
                "category": "Cancer cell line",
                "sex": "Female",
                "age": None,
                "species-list": [{"label": "Homo sapiens"}],
                "disease-list": [],
                "comment-list": [],
                "xref-list": [],
            }
        ]
    }
}


def test_get_cell_line_calls_http_get_json_and_maps_result() -> None:
    with patch.object(cellosaurus.http, "get_json", return_value=_FAKE_PAYLOAD) as mock_get_json:
        result = cellosaurus.get_cell_line("CVCL_0001")

    expected_query = urllib.parse.urlencode(
        {"format": "json", "fields": cellosaurus._COMPACT_FIELDS}
    )
    mock_get_json.assert_called_once_with(
        f"{cellosaurus.API_BASE}/cell-line/CVCL_0001?{expected_query}",
        headers={"Accept": "application/json"},
        timeout=40,
    )
    assert result is not None
    assert result["accession"] == "CVCL_0001"
    assert result["names"] == ["HeLa"]


_FAKE_CELLO_SEARCH_PAYLOAD: dict[str, object] = {
    "Cellosaurus": {
        "cell-line-list": [
            {
                "accession": "CVCL_0001",
                "name": "HeLa",
                "category": "Cancer cell line",
            }
        ]
    }
}


def test_cello_models_calls_http_get_json_with_expected_url_and_headers() -> None:
    with patch.object(
        cellosaurus.http, "get_json", return_value=_FAKE_CELLO_SEARCH_PAYLOAD
    ) as mock_get_json:
        result = cellosaurus.cello_models("Pancreatic cancer")

    (called_url,), called_kwargs = mock_get_json.call_args
    assert called_url.startswith(f"{cellosaurus._CELLO_SEARCH_URL}?")
    assert called_kwargs == {"headers": {"Accept": "application/json"}}
    assert result == [
        CellModelHit(id="CVCL_0001", name="HeLa", category="Cancer cell line", problematic=False)
    ]
