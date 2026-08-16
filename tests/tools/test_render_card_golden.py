from cellar.schemas.derivation import (
    MoaAction,
    MoaContext,
    MoaMember,
    MoaVerify,
    PathwayCoherence,
    PathwayMember,
)
from cellar.schemas.matchmaker import ModelCandidate, ModelTier, PathwayMemberStatus
from cellar.schemas.recommendation import ConditionState
from cellar.services.derivation.recommendation import build_card
from cellar.tools.scoring import score_candidate

_TARGET_CONTEXT: dict[str, object] = {"symbol": "ZDHHC20", "target_id": "ENSG00000180776"}
_ISOFORM_SUMMARY: dict[str, object] = {
    "isoform_specificity_risk": "high",
    "message": "Dominant isoform lacks catalytic domain in this tissue.",
}
_PROTEOMICS_SUMMARY: dict[str, object] = {
    "mrna_protein_discordant": True,
    "modalities": {"note": "Route via MS/CPTAC; olink not available."},
    "disease_protein_prognostic": {
        "Pancreatic cancer - protein X": {"is_prognostic": True, "prognostic type": "unfavorable"}
    },
}


def _pathway() -> PathwayCoherence:
    return PathwayCoherence(
        pathway_coherence=0.8,
        passed_science_gate=True,
        hard_fail=[],
        members=[
            PathwayMember(
                gene="GOLGA7",
                relation_type="stabilizer_accessory",
                gates=True,
                expression=0.8,
                status=PathwayMemberStatus.PRESENT,
                evidence_pmids=["11111111"],
                note="",
            ),
            PathwayMember(
                gene="KRAS",
                relation_type="substrate",
                gates=False,
                expression=0.9,
                status=PathwayMemberStatus.PRESENT,
                evidence_pmids=[],
                note="",
            ),
        ],
        verdict="Science gate PASS: enzyme intact and substrate/context co-expressed.",
    )


def _mechanism() -> MoaContext:
    return MoaContext(
        context_fit=0.9,
        context_required_unmet=False,
        actions=[
            MoaAction(
                condition="hypoxia_metabolic",
                action="culture in hypoxia chamber",
                cost="low",
                necessity="enhancing",
                readout_hint="HIF1A stabilization",
                evidence_pmids=[],
            ),
            MoaAction(
                condition="three_d_architecture",
                action="embed in matrigel",
                cost="medium",
                necessity="required",
                readout_hint="invasion assay",
                evidence_pmids=["33333333"],
            ),
        ],
        unmet_required=[],
        enhancing_missing=[],
        verify=[
            MoaVerify(
                condition="hypoxia_metabolic",
                rationale="tumor core hypoxia modulates palmitoylation flux",
            )
        ],
        members=[
            MoaMember(
                condition="three_d_architecture",
                necessity="required",
                state=ConditionState.NATIVE,
                retrofittable=False,
                rationale="PDAC stroma requires 3D architecture",
                readout_hint="invasion assay",
                evidence_pmids=["33333333"],
                cite="Smith et al 2020",
                needs_verification=False,
            ),
            MoaMember(
                condition="hypoxia_metabolic",
                necessity="enhancing",
                state=ConditionState.RETROFIT,
                retrofittable=True,
                rationale="tumor core hypoxia modulates flux",
                readout_hint="HIF1A stabilization",
                evidence_pmids=[],
                cite="",
                needs_verification=True,
            ),
        ],
        verdict="Mechanism observable; optional augmentations available to strengthen the readout.",
        question="target_validation",
        tier="2d_line",
    )


def _candidate(*, passed_science_gate: bool) -> ModelCandidate:
    candidate = ModelCandidate(
        name="MIA PaCa-2 (KRAS G12C, 2D)",
        tier=str(ModelTier.TWO_D_LINE),
        source="ATCC CRL-1420",
        catalog_url="https://www.atcc.org/products/crl-1420",
        mrna_expressed=0.9,
        protein_present=0.8,
        isoform_match=0.7,
        pathway_coherence=0.8,
        passed_science_gate=passed_science_gate,
        context_fit=0.9,
        context_required_unmet=False,
        disease_features_match=0.7,
        dependency_signal=0.6,
        genetic_tractable=0.95,
        provenance_ok=1.0,
        prior_use=0.5,
    )
    return score_candidate(candidate, "target_validation")


_EXPECTED_CONTEXT_NOTES = [
    "mRNA is broadly expressed but protein is not — do not rely on RNA-seq alone; confirm "
    "protein by WB/IF in your lot.",
    "Proteomics routing: Route via MS/CPTAC; olink not available.",
    "Isoform caveat: Dominant isoform lacks catalytic domain in this tissue.",
    "Protein-level disease signal: protein X (unfavorable).",
    "Mechanism needs three_d_architecture: embed in matrigel — invasion assay",
]

_EXPECTED_PASS_MARKDOWN = (
    "### MIA PaCa-2 (KRAS G12C, 2D)  [2d_line]  —  STRONG (overall 0.78)\n"
    "_Question: target_validation  |  Science 0.76 → Technical 0.81_\n"
    "\n"
    "**STEP 1 — Science gate: Science gate PASS: enzyme intact and substrate/context "
    "co-expressed.**\n"
    "  pathway coherence = 0.80\n"
    "  · GOLGA7 (stabilizer_accessory, GATES): present [PMID 11111111]\n"
    "  · KRAS (substrate, context): present [no direct paper]\n"
    "\n"
    "**STEP 1b — Mechanism context (fit 0.90): Mechanism observable; optional augmentations "
    "available to strengthen the readout.**\n"
    "  · three_d_architecture (required, native): PDAC stroma requires 3D architecture "
    "Smith et al 2020\n"
    "  · hypoxia_metabolic (enhancing, add-to-culture): tumor core hypoxia modulates flux \n"
    "  Culture actions to make the mechanism observable:\n"
    "    → hypoxia_metabolic: culture in hypoxia chamber (cost: low) -> unlocks: HIF1A "
    "stabilization\n"
    "    → three_d_architecture: embed in matrigel (cost: medium) -> unlocks: invasion assay\n"
    "    ? verify: hypoxia_metabolic: tumor core hypoxia modulates palmitoylation flux\n"
    "\n"
    "**STEP 2 — Why this model**\n"
    "  + Protein detected (MS/CPTAC) (0.80)\n"
    "  + Pathway relevance (substrate/context co-expressed) (0.80)\n"
    "  + Mechanism observable in this model (MoA context) (0.90)\n"
    "  + Expresses functional isoform (0.70)\n"
    "  + Carries disease drivers (0.70)\n"
    "  + Fits the biological question (0.70)\n"
    "  + CRISPR-tractable (0.95)\n"
    "  + Clean provenance (1.00)\n"
    "  + mRNA expressed (supporting) (0.90)\n"
    "\n"
    "**Watch-outs**\n"
    "  – No major weak dimensions.\n"
    "\n"
    "**Context for your decision**\n"
    "  • mRNA is broadly expressed but protein is not — do not rely on RNA-seq alone; confirm "
    "protein by WB/IF in your lot.\n"
    "  • Proteomics routing: Route via MS/CPTAC; olink not available.\n"
    "  • Isoform caveat: Dominant isoform lacks catalytic domain in this tissue.\n"
    "  • Protein-level disease signal: protein X (unfavorable).\n"
    "  • Mechanism needs three_d_architecture: embed in matrigel — invasion assay\n"
    "\n"
    "**Source:** ATCC CRL-1420 https://www.atcc.org/products/crl-1420"
)

_EXPECTED_REJECT_MARKDOWN = (
    "### MIA PaCa-2 (KRAS G12C, 2D)  [2d_line]  —  REJECTED — SCIENCE GATE (overall 0.35)\n"
    "_Question: target_validation  |  Science 0.76 → Technical 0.81_\n"
    "\n"
    "**STEP 1 — Science gate: Science gate PASS: enzyme intact and substrate/context "
    "co-expressed.**\n"
    "  pathway coherence = 0.80\n"
    "  · GOLGA7 (stabilizer_accessory, GATES): present [PMID 11111111]\n"
    "  · KRAS (substrate, context): present [no direct paper]\n"
    "\n"
    "**STEP 1b — Mechanism context (fit 0.90): Mechanism observable; optional augmentations "
    "available to strengthen the readout.**\n"
    "  · three_d_architecture (required, native): PDAC stroma requires 3D architecture "
    "Smith et al 2020\n"
    "  · hypoxia_metabolic (enhancing, add-to-culture): tumor core hypoxia modulates flux \n"
    "  Culture actions to make the mechanism observable:\n"
    "    → hypoxia_metabolic: culture in hypoxia chamber (cost: low) -> unlocks: HIF1A "
    "stabilization\n"
    "    → three_d_architecture: embed in matrigel (cost: medium) -> unlocks: invasion assay\n"
    "    ? verify: hypoxia_metabolic: tumor core hypoxia modulates palmitoylation flux\n"
    "\n"
    "**→ NOT RECOMMENDED: science_gate_failed. Technical suitability not assessed — fix the "
    "biology first.**\n"
    "\n"
    "**STEP 2 — Why this model**\n"
    "  + Protein detected (MS/CPTAC) (0.80)\n"
    "  + Pathway relevance (substrate/context co-expressed) (0.80)\n"
    "  + Mechanism observable in this model (MoA context) (0.90)\n"
    "  + Expresses functional isoform (0.70)\n"
    "  + Carries disease drivers (0.70)\n"
    "  + Fits the biological question (0.70)\n"
    "  + CRISPR-tractable (0.95)\n"
    "  + Clean provenance (1.00)\n"
    "  + mRNA expressed (supporting) (0.90)\n"
    "\n"
    "**Watch-outs**\n"
    "  – No major weak dimensions.\n"
    "\n"
    "**Context for your decision**\n"
    "  • mRNA is broadly expressed but protein is not — do not rely on RNA-seq alone; confirm "
    "protein by WB/IF in your lot.\n"
    "  • Proteomics routing: Route via MS/CPTAC; olink not available.\n"
    "  • Isoform caveat: Dominant isoform lacks catalytic domain in this tissue.\n"
    "  • Protein-level disease signal: protein X (unfavorable).\n"
    "  • Mechanism needs three_d_architecture: embed in matrigel — invasion assay\n"
    "\n"
    "**Source:** ATCC CRL-1420 https://www.atcc.org/products/crl-1420"
)


def test_render_card_golden_markdown_pass_gate_byte_identical() -> None:
    card = build_card(
        1,
        _candidate(passed_science_gate=True),
        "target_validation",
        _TARGET_CONTEXT,
        _ISOFORM_SUMMARY,
        _PROTEOMICS_SUMMARY,
        _pathway(),
        _mechanism(),
    )
    assert card.rendered_markdown == _EXPECTED_PASS_MARKDOWN
    assert card.context_notes == _EXPECTED_CONTEXT_NOTES


def test_render_card_golden_markdown_reject_gate_byte_identical() -> None:
    card = build_card(
        2,
        _candidate(passed_science_gate=False),
        "target_validation",
        _TARGET_CONTEXT,
        _ISOFORM_SUMMARY,
        _PROTEOMICS_SUMMARY,
        _pathway(),
        _mechanism(),
    )
    assert card.rendered_markdown == _EXPECTED_REJECT_MARKDOWN
    assert card.context_notes == _EXPECTED_CONTEXT_NOTES
