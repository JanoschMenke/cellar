from cellar.schemas.derivation import RankResult
from cellar.schemas.matchmaker import ModelCandidate, ModelTier, QuestionType
from cellar.tools import scoring


def _candidate(**overrides: object) -> ModelCandidate:
    base: dict[str, object] = {"name": "candidate", "tier": ModelTier.TWO_D_LINE.value}
    base.update(overrides)
    return ModelCandidate(**base)


def test_score_candidate_produces_deterministic_combined_score() -> None:
    candidate = _candidate(name="mid")

    scored = scoring.score_candidate(candidate, QuestionType.TARGET_VALIDATION)

    assert scored.scores is not None
    assert scored.scores.science_score == 0.58
    assert scored.scores.tech_score == 0.608
    assert scored.scores.gate == "passed"
    assert scored.scores.total == 0.59


def test_score_candidate_gates_on_low_protein_evidence() -> None:
    weak = _candidate(name="weak", protein_present=0.1)

    scored = scoring.score_candidate(weak, QuestionType.TARGET_VALIDATION)

    assert scored.scores is not None
    assert scored.scores.gate == "no_protein_evidence"
    assert scored.scores.total == 0.35


def test_rank_orders_by_score_descending_and_returns_documented_shape() -> None:
    weak = _candidate(name="weak", protein_present=0.1)
    strong = _candidate(
        name="strong",
        tier=ModelTier.ORGANOID.value,
        mrna_expressed=0.9,
        protein_present=0.9,
        isoform_match=0.9,
        pathway_coherence=0.9,
        context_fit=1.0,
        disease_features_match=0.9,
        dependency_signal=0.9,
        genetic_tractable=0.9,
        provenance_ok=1.0,
        prior_use=1.0,
    )

    ranked = scoring.rank([weak, strong], QuestionType.TARGET_VALIDATION)

    assert isinstance(ranked, RankResult)
    assert [row.name for row in ranked.ranked] == ["strong", "weak"]
    first_scores, second_scores = ranked.ranked[0].scores, ranked.ranked[1].scores
    assert first_scores is not None
    assert second_scores is not None
    assert first_scores.total > second_scores.total
    assert ranked.in_vivo_recommended is False


def test_go_in_vivo_verdict_true_when_all_candidates_are_weak() -> None:
    weak_one = scoring.score_candidate(
        _candidate(name="weak-one", protein_present=0.1), QuestionType.TARGET_VALIDATION
    )
    weak_two = scoring.score_candidate(
        _candidate(name="weak-two", protein_present=0.1), QuestionType.TARGET_VALIDATION
    )

    go_in_vivo, reason = scoring.go_in_vivo_verdict(
        [weak_one, weak_two], QuestionType.TARGET_VALIDATION
    )

    assert go_in_vivo is True
    assert reason == "No in-vitro model scores >0.45 (best=0.35); recommend GEMM/PDX in vivo."


def test_go_in_vivo_verdict_false_when_a_strong_candidate_exists() -> None:
    strong = scoring.score_candidate(
        _candidate(
            name="strong",
            tier=ModelTier.ORGANOID.value,
            mrna_expressed=0.9,
            protein_present=0.9,
            isoform_match=0.9,
            pathway_coherence=0.9,
            context_fit=1.0,
            disease_features_match=0.9,
            dependency_signal=0.9,
            genetic_tractable=0.9,
            provenance_ok=1.0,
            prior_use=1.0,
        ),
        QuestionType.TARGET_VALIDATION,
    )

    go_in_vivo, reason = scoring.go_in_vivo_verdict([strong], QuestionType.TARGET_VALIDATION)

    assert go_in_vivo is False
    assert reason == "Adequate in-vitro model exists (best=0.92)."
