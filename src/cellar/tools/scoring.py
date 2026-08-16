from cellar.schemas.derivation import CandidateScores, RankResult
from cellar.schemas.matchmaker import GateStatus, ModelCandidate
from cellar.schemas.scoring import (
    GATED_SCORE_CAP,
    IN_VIVO_MAX,
    ORGANISM_MAX,
    PATHWAY_GATE_MIN,
    PROTEIN_GATE_MIN,
    QUESTION_TIER_PRIOR,
    SCIENCE_BLEND,
    SCIENCE_W,
    TECH_BLEND,
    TECH_W,
    TIER_FIT_DEFAULT,
)

__all__ = [
    "QUESTION_TIER_PRIOR",
    "SCIENCE_W",
    "TECH_W",
    "score_candidate",
    "go_in_vivo_verdict",
    "rank",
]


def score_candidate(c: ModelCandidate, question_type: str) -> ModelCandidate:
    tier_fit = QUESTION_TIER_PRIOR.get(question_type, {}).get(c.tier, TIER_FIT_DEFAULT)
    science = dict(
        protein_present=c.protein_present,
        pathway_coherence=c.pathway_coherence,
        context_fit=c.context_fit,
        isoform_match=c.isoform_match,
        disease_features_match=c.disease_features_match,
        dependency_signal=c.dependency_signal,
    )
    tech = dict(
        tier_fit=tier_fit,
        genetic_tractable=c.genetic_tractable,
        provenance_ok=c.provenance_ok,
        prior_use=c.prior_use,
        mrna_expressed=c.mrna_expressed,
    )
    science_score = sum(SCIENCE_W[k] * v for k, v in science.items())
    tech_score = sum(TECH_W[k] * v for k, v in tech.items())

    gate_reason: GateStatus | None = None
    if not c.passed_science_gate:
        gate_reason = GateStatus.SCIENCE_GATE_FAILED
    elif c.context_required_unmet:
        gate_reason = GateStatus.MOA_CONTEXT_UNMET
    elif c.protein_present < PROTEIN_GATE_MIN:
        gate_reason = GateStatus.NO_PROTEIN_EVIDENCE
    elif c.pathway_coherence < PATHWAY_GATE_MIN:
        gate_reason = GateStatus.PATHWAY_INCOHERENT

    if gate_reason:
        total = min(science_score, GATED_SCORE_CAP)
    else:
        total = round(SCIENCE_BLEND * science_score + TECH_BLEND * tech_score, 3)

    rounded = {k: round(v, 3) for k, v in {**science, **tech}.items()}
    c.scores = CandidateScores(
        protein_present=rounded["protein_present"],
        pathway_coherence=rounded["pathway_coherence"],
        context_fit=rounded["context_fit"],
        isoform_match=rounded["isoform_match"],
        disease_features_match=rounded["disease_features_match"],
        dependency_signal=rounded["dependency_signal"],
        tier_fit=rounded["tier_fit"],
        genetic_tractable=rounded["genetic_tractable"],
        provenance_ok=rounded["provenance_ok"],
        prior_use=rounded["prior_use"],
        mrna_expressed=rounded["mrna_expressed"],
        science_score=round(science_score, 3),
        tech_score=round(tech_score, 3),
        gate=gate_reason or GateStatus.PASSED,
        total=round(total, 3),
    )
    return c


def _total_score(c: ModelCandidate) -> float:
    assert c.scores is not None
    return c.scores.total


def go_in_vivo_verdict(candidates: list[ModelCandidate], question_type: str) -> tuple[bool, str]:
    best = max((_total_score(c) for c in candidates if c.tier != "in_vivo"), default=0.0)
    needs_organism = question_type in ("efficacy", "immune_mechanism")
    if best < IN_VIVO_MAX:
        return (
            True,
            f"No in-vitro model scores >{IN_VIVO_MAX} (best={best:.2f}); recommend GEMM/PDX in vivo.",
        )
    if needs_organism and best < ORGANISM_MAX:
        return True, f"Question '{question_type}' needs an organism; best in-vitro only {best:.2f}."
    return False, f"Adequate in-vitro model exists (best={best:.2f})."


def rank(candidates: list[ModelCandidate], question_type: str) -> RankResult:
    scored = [score_candidate(c, question_type) for c in candidates]
    scored.sort(key=_total_score, reverse=True)
    go_vivo, why = go_in_vivo_verdict(scored, question_type)
    return RankResult(ranked=scored, in_vivo_recommended=go_vivo, verdict=why)
