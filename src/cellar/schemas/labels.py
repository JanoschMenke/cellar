from cellar.schemas.matchmaker import GateStatus, ModelTier
from cellar.schemas.recommendation import ConditionState
from cellar.schemas.verification import VerificationStatus

TIER_LABELS: dict[ModelTier, str] = {
    ModelTier.TWO_D_LINE: "2D cell line",
    ModelTier.ORGANOID: "Organoid",
    ModelTier.COCULTURE: "Co-culture",
    ModelTier.IN_VIVO: "In vivo (GEMM/PDX)",
}

VERDICT_LABELS: dict[GateStatus, str] = {
    GateStatus.PASSED: "Recommended",
    GateStatus.SCIENCE_GATE_FAILED: "Rejected — science gate",
    GateStatus.MOA_CONTEXT_UNMET: "Rejected — wrong model for this mechanism",
    GateStatus.NO_PROTEIN_EVIDENCE: "Rejected — no protein evidence",
    GateStatus.PATHWAY_INCOHERENT: "Rejected — pathway incoherent",
}

REJECT_LABELS: dict[str, str] = {
    "science_gate_failed": "REJECTED — science gate",
    "moa_context_unmet": "REJECTED — wrong model for this mechanism",
    "no_protein_evidence": "REJECTED — no protein evidence",
    "pathway_incoherent": "REJECTED — pathway incoherent",
}

SCIENCE_LABELS: dict[str, str] = {
    "protein_present": "Protein detected (MS/CPTAC)",
    "pathway_coherence": "Pathway relevance (substrate/context co-expressed)",
    "context_fit": "Mechanism observable in this model (MoA context)",
    "isoform_match": "Expresses functional isoform",
    "disease_features_match": "Carries disease drivers",
    "dependency_signal": "Target dependency (DepMap)",
}
TECH_LABELS: dict[str, str] = {
    "tier_fit": "Fits the biological question",
    "genetic_tractable": "CRISPR-tractable",
    "provenance_ok": "Clean provenance",
    "prior_use": "Prior use in literature",
    "mrna_expressed": "mRNA expressed (supporting)",
}
DIM_LABELS: dict[str, str] = {**SCIENCE_LABELS, **TECH_LABELS}

FACT_DIMS = (
    "protein_present",
    "pathway_coherence",
    "context_fit",
    "isoform_match",
    "disease_features_match",
    "dependency_signal",
)

DIM_PHRASING: dict[str, dict[str, str]] = {
    "protein_present": {
        "pro": "The protein itself is detected in this model, not just its mRNA.",
        "con": "Little or no protein detected here — mRNA presence alone won't validate the target.",
        "source": "Human Protein Atlas",
    },
    "pathway_coherence": {
        "pro": "Its pathway partners are co-expressed, so the target's signalling context is intact.",
        "con": "Key pathway partners are missing or low — the target's signalling context may be broken.",
        "source": "PubMed",
    },
    "context_fit": {
        "pro": "The mechanism you want to study can actually be read out in this model.",
        "con": "This model can't show the mechanism's readout without added culture conditions.",
        "source": "PubMed",
    },
    "isoform_match": {
        "pro": "Expresses the functional isoform with the catalytic domain intact.",
        "con": "The dominant isoform here lacks the functional region — you may assay the wrong protein.",
        "source": "Ensembl",
    },
    "disease_features_match": {
        "pro": "Carries the disease's driver alterations — the right genetic background.",
        "con": "Missing the expected disease-driver alterations — genetic background may not match.",
        "source": "Cell Model Passports / COSMIC",
    },
    "dependency_signal": {
        "pro": "Cells depend on this target in loss-of-function screens, so effects should be detectable.",
        "con": "Weak or absent dependency in screens — knockout effects may be hard to detect.",
        "source": "DepMap",
    },
}

VERIFICATION_STATUS_LABELS: dict[VerificationStatus, str] = {
    VerificationStatus.SOUND: "Verified — no issues found",
    VerificationStatus.CAVEATS: "Verified with caveats",
    VerificationStatus.NEEDS_ATTENTION: "Needs attention",
}

CONDITION_STATE_LABELS: dict[ConditionState, str] = {
    ConditionState.NATIVE: "native",
    ConditionState.RETROFIT: "add-to-culture",
    ConditionState.UNMET: "MISSING",
}
