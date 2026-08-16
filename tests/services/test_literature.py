from unittest.mock import patch

import pytest

from cellar.services.sources import literature
from cellar.utils import http

_FAKE_RESPONSE = {
    "hitCount": 1,
    "resultList": {
        "result": [
            {
                "title": "ZDHHC20 palmitoylation in pancreatic cancer",
                "authorString": "Doe J, Roe R",
                "pubYear": "2023",
                "abstractText": "We show ZDHHC20 drives PDAC growth.",
                "doi": "10.1000/xyz",
                "pmid": "12345678",
                "journalTitle": "Nature Cancer",
                "citedByCount": 42,
                "source": "MED",
            }
        ]
    },
}


def test_search_literature_maps_europepmc_fields() -> None:
    with patch.object(literature.http, "get_json", return_value=_FAKE_RESPONSE):
        result = literature.search_literature("ZDHHC20 PDAC", max_results=5)

    assert result["found"] is True
    assert result["n_results"] == 1
    paper = result["papers"][0]
    assert paper["title"].startswith("ZDHHC20")
    assert paper["year"] == 2023
    assert paper["pmid"] == "12345678"
    assert paper["doi"] == "10.1000/xyz"
    assert paper["cited_by_count"] == 42
    assert paper["is_preprint"] is False


def test_search_literature_flags_preprints() -> None:
    preprint = {
        "hitCount": 1,
        "resultList": {"result": [{**_FAKE_RESPONSE["resultList"]["result"][0], "source": "PPR"}]},
    }
    with patch.object(literature.http, "get_json", return_value=preprint):
        result = literature.search_literature("q")
    assert result["papers"][0]["is_preprint"] is True


def test_get_raises_runtime_error_with_exact_message_on_http_error() -> None:
    with (
        patch.object(literature.http, "get_json", side_effect=http.HttpError(400, "u", "bad")),
        pytest.raises(RuntimeError) as excinfo,
    ):
        literature._get("http://x")
    assert str(excinfo.value) == "Europe PMC error (400): bad"
