from cellar.schemas.derivation import (
    CandidateScores,
    MoaAction,
    MoaContext,
    MoaMember,
    MoaVerify,
    PathwayCoherence,
    PathwayMember,
    RankResult,
)
from cellar.schemas.matchmaker import GateStatus, ModelCandidate, PathwayMemberStatus
from cellar.schemas.recommendation import ConditionState


def test_candidate_scores_round_trips_and_has_exactly_fifteen_fields() -> None:
    data = {
        "protein_present": 0.8,
        "pathway_coherence": 0.6,
        "context_fit": 1.0,
        "isoform_match": 0.5,
        "disease_features_match": 0.5,
        "dependency_signal": 0.5,
        "tier_fit": 0.7,
        "genetic_tractable": 0.5,
        "provenance_ok": 1.0,
        "prior_use": 0.0,
        "mrna_expressed": 0.5,
        "science_score": 0.65,
        "tech_score": 0.55,
        "gate": GateStatus.PASSED,
        "total": 0.61,
    }
    model = CandidateScores(**data)
    assert model.model_dump() == data
    assert set(CandidateScores.model_fields) == set(data)
    assert len(CandidateScores.model_fields) == 15


def test_pathway_member_round_trips() -> None:
    data = {
        "gene": "KRAS",
        "relation_type": "substrate",
        "gates": True,
        "expression": 0.9,
        "status": PathwayMemberStatus.PRESENT,
        "evidence_pmids": ["123", "456"],
        "note": "strong co-expression",
    }
    model = PathwayMember(**data)
    assert model.model_dump() == data


def test_pathway_coherence_round_trips() -> None:
    member = {
        "gene": "KRAS",
        "relation_type": "substrate",
        "gates": True,
        "expression": 0.9,
        "status": PathwayMemberStatus.PRESENT,
        "evidence_pmids": [],
        "note": "",
    }
    data = {
        "pathway_coherence": 0.75,
        "passed_science_gate": True,
        "hard_fail": [],
        "members": [member],
        "verdict": "Science gate PASS: enzyme intact and substrate/context co-expressed.",
    }
    model = PathwayCoherence(**data)
    assert model.model_dump() == data


def test_moa_member_round_trips() -> None:
    data = {
        "condition": "hypoxia",
        "necessity": "required",
        "state": ConditionState.NATIVE,
        "retrofittable": False,
        "rationale": "tumor core is hypoxic",
        "readout_hint": "HIF1A stabilization",
        "evidence_pmids": ["789"],
        "cite": "[PMID 789]",
        "needs_verification": False,
    }
    model = MoaMember(**data)
    assert model.model_dump() == data


def test_moa_action_round_trips() -> None:
    data = {
        "condition": "stromal_coculture",
        "action": "add CAFs",
        "cost": "medium",
        "necessity": "enhancing",
        "readout_hint": "paracrine signaling",
        "evidence_pmids": [],
    }
    model = MoaAction(**data)
    assert model.model_dump() == data


def test_moa_verify_round_trips() -> None:
    data = {"condition": "immune_infiltration", "rationale": "hypothesis pending validation"}
    model = MoaVerify(**data)
    assert model.model_dump() == data


def test_moa_context_round_trips() -> None:
    data = {
        "context_fit": 0.5,
        "context_required_unmet": False,
        "actions": [
            {
                "condition": "stromal_coculture",
                "action": "add CAFs",
                "cost": "medium",
                "necessity": "enhancing",
                "readout_hint": "paracrine signaling",
                "evidence_pmids": [],
            }
        ],
        "unmet_required": [],
        "enhancing_missing": ["stromal_coculture"],
        "verify": [{"condition": "immune_infiltration", "rationale": "hypothesis pending"}],
        "members": [
            {
                "condition": "hypoxia",
                "necessity": "required",
                "state": ConditionState.NATIVE,
                "retrofittable": False,
                "rationale": "tumor core is hypoxic",
                "readout_hint": "HIF1A stabilization",
                "evidence_pmids": ["789"],
                "cite": "[PMID 789]",
                "needs_verification": False,
            }
        ],
        "verdict": "Model natively supports the mechanism's context requirements.",
        "question": "efficacy",
        "tier": "organoid",
    }
    model = MoaContext(**data)
    assert model.model_dump() == data


def test_rank_result_round_trips() -> None:
    scores = CandidateScores(
        protein_present=0.5,
        pathway_coherence=0.5,
        context_fit=1.0,
        isoform_match=0.5,
        disease_features_match=0.5,
        dependency_signal=0.5,
        tier_fit=0.5,
        genetic_tractable=0.5,
        provenance_ok=1.0,
        prior_use=0.0,
        mrna_expressed=0.5,
        science_score=0.5,
        tech_score=0.5,
        gate=GateStatus.PASSED,
        total=0.9,
    )
    candidate = ModelCandidate(
        name="HCT116",
        tier="2d_line",
        source="ATCC",
        catalog_url="https://example.com",
        scores=scores,
    )
    data = {
        "ranked": [candidate],
        "in_vivo_recommended": False,
        "verdict": "Adequate in-vitro model exists (best=0.90).",
    }
    model = RankResult(**data)
    dumped = model.model_dump()
    assert dumped["in_vivo_recommended"] is False
    assert dumped["verdict"] == data["verdict"]
    assert dumped["ranked"] == [
        {
            "name": "HCT116",
            "tier": "2d_line",
            "source": "ATCC",
            "catalog_url": "https://example.com",
            "mrna_expressed": 0.5,
            "protein_present": 0.5,
            "isoform_match": 0.5,
            "pathway_coherence": 0.5,
            "passed_science_gate": True,
            "context_fit": 1.0,
            "context_required_unmet": False,
            "disease_features_match": 0.5,
            "dependency_signal": 0.5,
            "genetic_tractable": 0.5,
            "provenance_ok": 1.0,
            "prior_use": 0.0,
            "scores": scores.model_dump(),
        }
    ]
