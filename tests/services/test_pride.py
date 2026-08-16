from unittest.mock import patch

from cellar.schemas.sources import UniprotHit
from cellar.services.sources import pride

_FAKE_SEARCH: dict[str, object] = {
    "results": [{"primaryAccession": "Q5W0Z9", "proteinExistence": "1: Evidence at protein level"}]
}


def test_resolve_uniprot_calls_http_get_json_and_maps_result() -> None:
    with patch.object(pride.http, "get_json", return_value=_FAKE_SEARCH) as mock_get_json:
        result = pride.resolve_uniprot("ZDHHC20")

    assert mock_get_json.call_count == 1
    (called_url,), called_kwargs = mock_get_json.call_args
    assert called_url.startswith(f"{pride._UNIPROT}?")
    assert "ZDHHC20" in called_url
    assert called_kwargs == {"headers": {"Accept": "application/json"}, "timeout": 30}

    assert result == UniprotHit(accession="Q5W0Z9", protein_existence_level=1)
