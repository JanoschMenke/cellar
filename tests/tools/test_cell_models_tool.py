import json
from unittest.mock import patch

from cellar.services.sources import cell_model_passports as cmp
from cellar.tools.cell_models import CellModelGeneMutationsTool, FindCellModelTool


def test_find_cell_model_valid_dispatch_calls_service() -> None:
    tool = FindCellModelTool()
    with patch(
        "cellar.tools.cell_models.cmp.model_facts",
        return_value={"id": "SIDM00505"},
    ) as spy:
        result = tool.dispatch({"name": "MIA PaCa-2"})
    spy.assert_called_once_with("MIA PaCa-2")
    assert result.is_error is False


_FAKE_LIST_MODELS_PAYLOAD: dict[str, object] = {
    "meta": {"count": 1},
    "data": [
        {
            "id": "SIDM00842",
            "type": "models",
            "attributes": {
                "names": ["MIA PaCa-2"],
                "model_type": "Cell line",
                "growth_properties": "Adherent",
                "ploidy": 2.9,
                "mutations_per_mb": 3.4,
                "crispr_ko_available": True,
                "mutations_available": True,
                "cnv_available": True,
            },
        }
    ],
    "links": {},
}

_EXPECTED_FIND_CELL_MODEL_JSON = {
    "found": True,
    "sidm_id": "SIDM00842",
    "names": ["MIA PaCa-2"],
    "model_type": "Cell line",
    "growth_properties": "Adherent",
    "ploidy": 2.9,
    "mutations_per_mb": 3.4,
    "crispr_ko_available": True,
    "datasets_available": ["mutations", "cnv", "crispr_ko"],
    "catalog_url": "https://cellmodelpassports.sanger.ac.uk/passports/SIDM00842",
}


def test_find_cell_model_tool_json_matches_pre_refactor_shape() -> None:
    tool = FindCellModelTool()
    with patch.object(cmp, "_fetch", return_value=_FAKE_LIST_MODELS_PAYLOAD):
        result = tool.dispatch({"name": "MIA PaCa-2"})
    assert result.is_error is False
    assert json.loads(result.content) == _EXPECTED_FIND_CELL_MODEL_JSON


def test_find_cell_model_missing_required_skips_service() -> None:
    tool = FindCellModelTool()
    with patch("cellar.tools.cell_models.cmp.model_facts") as spy:
        result = tool.dispatch({})
    assert result.is_error is True
    spy.assert_not_called()


def test_cell_model_gene_mutations_valid_dispatch_calls_service() -> None:
    tool = CellModelGeneMutationsTool()
    with patch(
        "cellar.tools.cell_models.cmp.model_gene_mutations",
        return_value={"records": []},
    ) as spy:
        result = tool.dispatch({"model": "SIDM00505", "gene_symbol": "KRAS"})
    spy.assert_called_once_with("SIDM00505", "KRAS")
    assert result.is_error is False


def test_cell_model_gene_mutations_missing_required_skips_service() -> None:
    tool = CellModelGeneMutationsTool()
    with patch("cellar.tools.cell_models.cmp.model_gene_mutations") as spy:
        result = tool.dispatch({"model": "SIDM00505"})
    assert result.is_error is True
    spy.assert_not_called()
