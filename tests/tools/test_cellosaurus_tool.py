import json
from unittest.mock import patch

from cellar.services.sources import cellosaurus
from cellar.tools.cellosaurus import CellLineProvenanceTool


def test_cell_line_provenance_valid_dispatch_calls_service() -> None:
    tool = CellLineProvenanceTool()
    with patch(
        "cellar.tools.cellosaurus.cellosaurus.provenance",
        return_value={"found": True},
    ) as spy:
        result = tool.dispatch({"name": "PANC-1"})
    spy.assert_called_once_with("PANC-1")
    assert result.is_error is False


def test_cell_line_provenance_missing_required_skips_service() -> None:
    tool = CellLineProvenanceTool()
    with patch("cellar.tools.cellosaurus.cellosaurus.provenance") as spy:
        result = tool.dispatch({})
    assert result.is_error is True
    spy.assert_not_called()


_FAKE_SEARCH_PAYLOAD: dict[str, object] = {
    "Cellosaurus": {
        "cell-line-list": [
            {
                "accession-list": [{"type": "primary", "value": "CVCL_0480"}],
                "name-list": [{"value": "PANC-1"}],
                "category": "Cancer cell line",
                "sex": "Male",
                "age": "56Y",
                "species-list": [{"label": "Homo sapiens"}],
                "disease-list": [],
                "comment-list": [
                    {"category": "Caution", "value": "Some caution text"},
                ],
                "xref-list": [
                    {
                        "database": "ATCC",
                        "accession": "CRL-1469",
                        "url": "https://www.atcc.org/CRL-1469",
                        "category": "Cell line collections (Providers)",
                    },
                    {
                        "database": "Cell_Model_Passport",
                        "accession": "SIDM00midEx",
                        "url": "https://cellmodelpassports.sanger.ac.uk/x",
                        "category": "Biological resource",
                    },
                ],
            }
        ]
    }
}

_EXPECTED_PROVENANCE_JSON = {
    "found": True,
    "accession": "CVCL_0480",
    "names": ["PANC-1"],
    "category": "Cancer cell line",
    "species": ["Homo sapiens"],
    "problematic": False,
    "problems": [],
    "cautions": ["Some caution text"],
    "provenance_ok": 1.0,
    "commercial_listings": {
        "ATCC": {"accession": "CRL-1469", "url": "https://www.atcc.org/CRL-1469"}
    },
    "cross_ids": {"cell_model_passport": "SIDM00midEx"},
    "cellosaurus_url": "https://www.cellosaurus.org/CVCL_0480",
}


def test_cell_line_provenance_tool_json_matches_pre_refactor_shape() -> None:
    tool = CellLineProvenanceTool()
    with patch.object(cellosaurus.http, "get_json", return_value=_FAKE_SEARCH_PAYLOAD):
        result = tool.dispatch({"name": "PANC-1"})
    assert result.is_error is False
    assert json.loads(result.content) == _EXPECTED_PROVENANCE_JSON
