from cellar.services.derivation.aggregate import _gathered_model_names
from cellar.services.evidence_store import EvidenceStore

_HT29_PASSPORT: dict[str, object] = {
    "found": True,
    "sidm_id": "SIDM00136",
    "model_names": ["HT-29"],
}


def _store(*records: tuple[str, dict[str, object], dict[str, object]]) -> EvidenceStore:
    store = EvidenceStore()
    for tool, tool_input, data in records:
        store.record(tool, tool_input, data)
    return store


def test_a_model_looked_up_by_name_then_by_sidm_id_yields_one_candidate() -> None:
    store = _store(
        ("find_cell_model", {"name": "HT-29"}, _HT29_PASSPORT),
        (
            "gene_dependency",
            {"gene_symbol": "KRAS", "model": "SIDM00136"},
            {"found": True, "model_id": "SIDM00136", "model_names": ["HT-29"]},
        ),
    )

    assert _gathered_model_names(store) == ["HT-29"]


def test_a_model_looked_up_by_name_then_by_synonym_yields_one_candidate() -> None:
    store = _store(
        (
            "find_cell_model",
            {"name": "Caco-2"},
            {"found": True, "sidm_id": "SIDM00891", "model_names": ["Caco-2", "CACO2/TC7"]},
        ),
        (
            "cell_model_gene_mutations",
            {"model": "CACO2/TC7", "gene_symbol": "KRAS"},
            {"found": True, "model_id": "SIDM00891"},
        ),
    )

    assert _gathered_model_names(store) == ["Caco-2"]


def test_a_model_looked_up_by_name_then_by_cellosaurus_accession_yields_one_candidate() -> None:
    store = _store(
        (
            "cell_line_provenance",
            {"name": "MIA PaCa-2"},
            {"found": True, "accession": "CVCL_0428", "names": ["MIA PaCa-2"]},
        ),
        (
            "gene_dependency",
            {"gene_symbol": "KRAS", "model": "CVCL_0428"},
            {"found": True, "accession": "CVCL_0428"},
        ),
    )

    assert _gathered_model_names(store) == ["MIA PaCa-2"]


def test_cross_referenced_ids_join_records_from_different_databases() -> None:
    store = _store(
        (
            "cell_line_provenance",
            {"name": "HT-29"},
            {"found": True, "accession": "CVCL_0320", "cross_ids": {"sidm": "SIDM00136"}},
        ),
        ("find_cell_model", {"name": "SIDM00136"}, _HT29_PASSPORT),
    )

    assert _gathered_model_names(store) == ["HT-29"]


def test_distinct_models_are_still_ranked_separately() -> None:
    store = _store(
        ("find_cell_model", {"name": "HT-29"}, _HT29_PASSPORT),
        (
            "find_cell_model",
            {"name": "PANC-1"},
            {"found": True, "sidm_id": "SIDM00499", "model_names": ["PANC-1"]},
        ),
    )

    assert _gathered_model_names(store) == ["HT-29", "PANC-1"]


def test_spelling_variants_of_one_name_still_collapse_without_any_ids() -> None:
    store = _store(
        ("find_cell_model", {"name": "HT-29"}, {"found": True}),
        ("gene_dependency", {"gene_symbol": "KRAS", "model": "ht29"}, {"found": True}),
    )

    assert _gathered_model_names(store) == ["HT-29"]
