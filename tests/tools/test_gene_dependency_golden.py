import json
from unittest.mock import patch

from cellar.tools.dependency import GeneDependencyTool

FIND_GENE_KRAS: dict[str, object] = {"id": "SIDG00001"}
FIND_MODEL_MIA_PACA: dict[str, object] = {"id": "SIDM00636", "names": ["MIA PaCa-2"]}

RECORDS_SCREENED_WITH_BF: list[dict[str, object]] = [
    {"fc_clean_qn": -0.8, "bf_scaled": 12.0, "qc_pass": True, "source": "Broad"},
    {"fc_clean_qn": -0.6, "bf_scaled": 10.0, "qc_pass": True, "source": "Sanger"},
]

RECORDS_SCREENED_NULL_BF: list[dict[str, object]] = [
    {"fc_clean_qn": -0.9, "bf_scaled": None, "qc_pass": True, "source": "Broad"},
]

RECORDS_SUMMARY_SCREENED: list[dict[str, object]] = [
    {"fc_clean_qn": -0.8, "relationships": {"model": "SIDM001"}},
    {"fc_clean_qn": -0.2, "relationships": {"model": "SIDM002"}},
    {"fc_clean_qn": -0.9, "relationships": {"model": "SIDM003"}},
]

EXPECTED_MODEL_SCREENED_WITH_BF: dict[str, object] = {
    "found": True,
    "gene_symbol": "KRAS",
    "gene_id": "SIDG00001",
    "model_id": "SIDM00636",
    "model_names": ["MIA PaCa-2"],
    "n_measurements": 2,
    "screened": True,
    "gene_effect": -0.7,
    "bf_scaled": 11.0,
    "qc_pass": True,
    "source": ["Broad", "Sanger"],
    "is_dependency": True,
    "dependency_signal": 0.35,
    "reference": "https://depmap.org/portal/gene/KRAS",
    "model_reference": "https://cellmodelpassports.sanger.ac.uk/passports/SIDM00636",
}

EXPECTED_MODEL_SCREENED_NULL_BF: dict[str, object] = {
    "found": True,
    "gene_symbol": "KRAS",
    "gene_id": "SIDG00001",
    "model_id": "SIDM00636",
    "model_names": ["MIA PaCa-2"],
    "n_measurements": 1,
    "screened": True,
    "gene_effect": -0.9,
    "bf_scaled": None,
    "qc_pass": True,
    "source": ["Broad"],
    "is_dependency": True,
    "dependency_signal": 0.45,
    "reference": "https://depmap.org/portal/gene/KRAS",
    "model_reference": "https://cellmodelpassports.sanger.ac.uk/passports/SIDM00636",
}

EXPECTED_MODEL_UNSCREENED: dict[str, object] = {
    "found": True,
    "gene_symbol": "KRAS",
    "gene_id": "SIDG00001",
    "model_id": "SIDM00636",
    "model_names": ["MIA PaCa-2"],
    "n_measurements": 0,
    "screened": False,
    "note": "no CRISPR knockout screen for this gene in this model",
    "reference": "https://depmap.org/portal/gene/KRAS",
    "model_reference": "https://cellmodelpassports.sanger.ac.uk/passports/SIDM00636",
}

EXPECTED_GENE_NOT_FOUND: dict[str, object] = {
    "found": False,
    "reason": "gene not found: NOPE",
    "reference": "https://depmap.org/portal/gene/NOPE",
}

EXPECTED_MODEL_NOT_FOUND: dict[str, object] = {
    "found": False,
    "reason": "model not found: NoSuchModel",
    "reference": "https://depmap.org/portal/gene/KRAS",
}

EXPECTED_SUMMARY_SCREENED: dict[str, object] = {
    "found": True,
    "gene_symbol": "KRAS",
    "gene_id": "SIDG00001",
    "n_models": 3,
    "screened": True,
    "truncated": False,
    "mean_gene_effect": -0.633,
    "n_dependent_models": 2,
    "fraction_dependent": 0.667,
    "strongest": {"model_id": "SIDM003", "gene_effect": -0.9},
    "dependency_signal": 0.317,
    "reference": "https://depmap.org/portal/gene/KRAS",
}

EXPECTED_SUMMARY_UNSCREENED: dict[str, object] = {
    "found": True,
    "gene_symbol": "KRAS",
    "gene_id": "SIDG00001",
    "n_models": 0,
    "screened": False,
    "note": "gene not present in the CRISPR screen dataset",
    "reference": "https://depmap.org/portal/gene/KRAS",
}

EXPECTED_SUMMARY_GENE_NOT_FOUND: dict[str, object] = {
    "found": False,
    "reason": "gene not found: NOPE",
    "reference": "https://depmap.org/portal/gene/NOPE",
}


def _run(
    gene_symbol: str,
    model: str | None,
    find_gene_return: dict[str, object] | None,
    find_model_return: dict[str, object] | None,
    get_collection_return: dict[str, object],
) -> str:
    tool = GeneDependencyTool()
    arguments: dict[str, object] = {"gene_symbol": gene_symbol}
    if model is not None:
        arguments["model"] = model
    with (
        patch(
            "cellar.services.derivation.dependency.cmp.find_gene",
            return_value=find_gene_return,
        ),
        patch(
            "cellar.services.derivation.dependency.cmp.find_model",
            return_value=find_model_return,
        ),
        patch(
            "cellar.services.derivation.dependency.cmp.get_collection",
            return_value=get_collection_return,
        ),
    ):
        result = tool.dispatch(arguments)
    assert result.is_error is False, result.content
    return result.content


def test_gene_effect_in_model_screened_with_bf_scaled_matches_pre_refactor_shape() -> None:
    content = _run(
        "KRAS",
        "MIA PaCa-2",
        FIND_GENE_KRAS,
        FIND_MODEL_MIA_PACA,
        {"records": RECORDS_SCREENED_WITH_BF, "truncated": False},
    )
    assert json.loads(content) == EXPECTED_MODEL_SCREENED_WITH_BF


def test_gene_effect_in_model_screened_null_bf_scaled_matches_pre_refactor_shape() -> None:
    content = _run(
        "KRAS",
        "MIA PaCa-2",
        FIND_GENE_KRAS,
        FIND_MODEL_MIA_PACA,
        {"records": RECORDS_SCREENED_NULL_BF, "truncated": False},
    )
    parsed = json.loads(content)
    assert parsed == EXPECTED_MODEL_SCREENED_NULL_BF
    assert parsed["bf_scaled"] is None


def test_gene_effect_in_model_unscreened_matches_pre_refactor_shape() -> None:
    content = _run(
        "KRAS",
        "MIA PaCa-2",
        FIND_GENE_KRAS,
        FIND_MODEL_MIA_PACA,
        {"records": [], "truncated": False},
    )
    assert json.loads(content) == EXPECTED_MODEL_UNSCREENED


def test_gene_effect_in_model_gene_not_found_matches_pre_refactor_shape() -> None:
    content = _run(
        "NOPE",
        "MIA PaCa-2",
        None,
        None,
        {"records": [], "truncated": False},
    )
    assert json.loads(content) == EXPECTED_GENE_NOT_FOUND


def test_gene_effect_in_model_model_not_found_matches_pre_refactor_shape() -> None:
    content = _run(
        "KRAS",
        "NoSuchModel",
        FIND_GENE_KRAS,
        None,
        {"records": [], "truncated": False},
    )
    assert json.loads(content) == EXPECTED_MODEL_NOT_FOUND


def test_gene_dependency_summary_screened_matches_pre_refactor_shape() -> None:
    content = _run(
        "KRAS",
        None,
        FIND_GENE_KRAS,
        None,
        {"records": RECORDS_SUMMARY_SCREENED, "truncated": False},
    )
    assert json.loads(content) == EXPECTED_SUMMARY_SCREENED


def test_gene_dependency_summary_unscreened_matches_pre_refactor_shape() -> None:
    content = _run(
        "KRAS",
        None,
        FIND_GENE_KRAS,
        None,
        {"records": [], "truncated": False},
    )
    assert json.loads(content) == EXPECTED_SUMMARY_UNSCREENED


def test_gene_dependency_summary_gene_not_found_matches_pre_refactor_shape() -> None:
    content = _run(
        "NOPE",
        None,
        None,
        None,
        {"records": [], "truncated": False},
    )
    assert json.loads(content) == EXPECTED_SUMMARY_GENE_NOT_FOUND
