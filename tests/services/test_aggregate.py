from unittest.mock import patch

from cellar.schemas.matchmaker import (
    FactsSummary,
    GateStatus,
    MatchmakerQuery,
    ModelTier,
    QuestionType,
)
from cellar.schemas.recommendation import (
    RecommendationCard,
    RecommendationReport,
    ScoreBreakdown,
    Strength,
)
from cellar.services.derivation.aggregate import aggregate_recommendations
from cellar.services.evidence_store import EvidenceStore

_QUERY = MatchmakerQuery(
    target_symbol="ZDHHC20",
    disease="pancreatic cancer",
    question_type=QuestionType.TARGET_VALIDATION,
)


def test_aggregate_recommendations_reports_no_models_when_store_is_empty() -> None:
    store = EvidenceStore()

    report = aggregate_recommendations(store, _QUERY)

    assert report.cards == []
    assert report.in_vivo_recommended is False
    assert "No candidate cell-line models have been investigated for ZDHHC20" in report.verdict


def _populated_store() -> EvidenceStore:
    store = EvidenceStore()
    store.record(
        "find_cell_model",
        {"name": "SUIT-2"},
        {
            "found": True,
            "sidm_id": "SIDM00045",
            "model_type": "Adherent Cell Line",
            "crispr_ko_available": True,
            "datasets_available": ["expression", "mutation"],
            "growth_properties": "Adherent",
            "ploidy": 2.9,
            "names": ["SUIT-2 (display)"],
        },
    )
    store.record(
        "cell_line_provenance",
        {"name": "SUIT-2"},
        {
            "found": True,
            "category": "Cancer cell line",
            "accession": "CVCL_3172",
            "cellosaurus_url": "https://www.cellosaurus.org/CVCL_3172",
            "problematic": False,
            "commercial_listings": {
                "JCRB": {"accession": "JCRB1094", "url": "https://cellbank.nibiohn.go.jp/JCRB1094"}
            },
            "provenance_ok": 1.0,
        },
    )
    store.record(
        "cell_model_gene_mutations",
        {"model": "SUIT-2", "gene_symbol": "ZDHHC20"},
        {
            "found": True,
            "gene_symbol": "ZDHHC20",
            "mutations": [
                {"cancer_driver": True, "protein": "p.G12D", "effect": "missense", "vaf": 0.42}
            ],
        },
    )
    store.record(
        "gene_dependency",
        {"model": "SUIT-2", "gene_symbol": "ZDHHC20"},
        {
            "found": True,
            "is_dependency": True,
            "gene_effect": -0.8,
            "bf_scaled": 12.3,
            "dependency_signal": 0.9,
        },
    )
    return store


def _canned_report() -> RecommendationReport:
    card = RecommendationCard(
        rank=1,
        model_name="SUIT-2",
        tier=ModelTier.TWO_D_LINE,
        tier_label="2D line",
        question=QuestionType.TARGET_VALIDATION,
        recommended=True,
        gate=GateStatus.PASSED,
        verdict_label="Recommended",
        confidence=Strength.STRONG,
        headline="Good fit",
        scores=ScoreBreakdown(overall=0.9),
    )
    return RecommendationReport(
        query=_QUERY,
        verdict="stub verdict",
        in_vivo_recommended=False,
        facts=FactsSummary(),
        cards=[card],
    )


def test_aggregate_recommendations_enriches_card_from_evidence_store() -> None:
    store = _populated_store()

    with patch(
        "cellar.services.derivation.aggregate.run_matchmaker", return_value=_canned_report()
    ) as run_matchmaker_spy:
        report = aggregate_recommendations(store, _QUERY)

    assert run_matchmaker_spy.called
    card = report.cards[0]
    assert card.model_name == "SUIT-2 (display)"
    assert card.sourcing.purchasable is True
    reason_keys = {reason.key for reason in card.reasons}
    assert reason_keys == {"mutation:ZDHHC20", "dependency", "datasets", "growth", "provenance"}
    assert card.watch_outs == []
