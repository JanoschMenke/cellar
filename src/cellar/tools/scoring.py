"""
Scoring + tier rubric — Person B owns this file.
Deterministic scores from retrieved facts; the LLM judge (judge.py) writes the
prose rationale on top. Keeping scoring deterministic is what makes the output
defensible and reproducible for the demo.

The 10 decision dimensions from the design doc, collapsed into 6 computable
signals + 4 that come from the evidence layer (Elicit/Amass).
"""
from dataclasses import asdict

from cellar.schemas.matchmaker import ModelCandidate

# Question type -> which model tier the biology actually calls for.
# This is the "2D -> 3D -> co-culture -> in vivo" ladder, keyed on intent.
QUESTION_TIER_PRIOR: dict[str, dict[str, float]] = {
    "hts_screen":        {"2d_line": 1.0, "organoid": 0.5, "coculture": 0.2, "in_vivo": 0.0},
    "target_validation": {"2d_line": 0.7, "organoid": 0.9, "coculture": 0.6, "in_vivo": 0.4},
    "mechanism":         {"2d_line": 0.5, "organoid": 0.9, "coculture": 0.8, "in_vivo": 0.6},
    "immune_mechanism":  {"2d_line": 0.1, "organoid": 0.6, "coculture": 1.0, "in_vivo": 0.8},
    "efficacy":          {"2d_line": 0.3, "organoid": 0.7, "coculture": 0.6, "in_vivo": 1.0},
}

# Two-stage scoring. STAGE 1 = SCIENCE (does the biology hold in this model):
# protein present, right isoform, pathway coherent, disease drivers, dependency.
# STAGE 2 = TECHNICAL suitability (only meaningful once the science passes):
# tier fit, genetic tractability, provenance, prior use.
SCIENCE_W = dict(protein_present=0.24, pathway_coherence=0.20, context_fit=0.16,
                 isoform_match=0.10, disease_features_match=0.18, dependency_signal=0.12)
TECH_W = dict(tier_fit=0.34, genetic_tractable=0.22, provenance_ok=0.22,
              prior_use=0.14, mrna_expressed=0.08)

def score_candidate(c: ModelCandidate, question_type: str) -> ModelCandidate:
    tier_fit = QUESTION_TIER_PRIOR.get(question_type, {}).get(c.tier, 0.5)
    science = dict(protein_present=c.protein_present, pathway_coherence=c.pathway_coherence,
                   context_fit=c.context_fit, isoform_match=c.isoform_match,
                   disease_features_match=c.disease_features_match,
                   dependency_signal=c.dependency_signal)
    tech = dict(tier_fit=tier_fit, genetic_tractable=c.genetic_tractable,
                provenance_ok=c.provenance_ok, prior_use=c.prior_use,
                mrna_expressed=c.mrna_expressed)
    science_score = sum(SCIENCE_W[k] * v for k, v in science.items())
    tech_score = sum(TECH_W[k] * v for k, v in tech.items())

    # HARD GATES — science must hold first, or technical convenience can't rescue it.
    gate_reason = None
    if not c.passed_science_gate:
        gate_reason = "science_gate_failed"          # required cofactor/upstream absent
    elif c.context_required_unmet:
        gate_reason = "moa_context_unmet"            # right target, wrong model: the
                                                     # mechanism's readout can't exist here
    elif c.protein_present < 0.3:
        gate_reason = "no_protein_evidence"          # mRNA alone can't rescue
    elif c.pathway_coherence < 0.35:
        gate_reason = "pathway_incoherent"           # target present but pathway broken

    if gate_reason:
        # Technical score is withheld — a broken-science model is not "80% good".
        total = min(science_score, 0.35)
    else:
        # Science dominates; technical suitability is a multiplier on a passing model.
        total = round(0.65 * science_score + 0.35 * tech_score, 3)

    c.scores = {**{k: round(v, 3) for k, v in {**science, **tech}.items()},
                "science_score": round(science_score, 3),
                "tech_score": round(tech_score, 3),
                "gate": gate_reason or "passed",
                "total": round(total, 3)}
    return c

def go_in_vivo_verdict(candidates: list[ModelCandidate], question_type: str) -> tuple[bool, str]:
    """The honest fallback: if no in-vitro candidate clears the bar for the
    biological question, recommend in vivo / build-a-model. Cheap and it's the
    most credible, differentiating feature."""
    best = max((c.scores["total"] for c in candidates if c.tier != "in_vivo"), default=0)
    needs_organism = question_type in ("efficacy", "immune_mechanism")
    if best < 0.45:
        return True, f"No in-vitro model scores >0.45 (best={best:.2f}); recommend GEMM/PDX in vivo."
    if needs_organism and best < 0.6:
        return True, f"Question '{question_type}' needs an organism; best in-vitro only {best:.2f}."
    return False, f"Adequate in-vitro model exists (best={best:.2f})."

def rank(candidates: list[ModelCandidate], question_type: str) -> dict[str, object]:
    scored = [score_candidate(c, question_type) for c in candidates]
    scored.sort(key=lambda c: c.scores["total"], reverse=True)
    go_vivo, why = go_in_vivo_verdict(scored, question_type)
    return {"ranked": [asdict(c) for c in scored],
            "in_vivo_recommended": go_vivo, "verdict": why}
