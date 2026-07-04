from cellar.schemas.matchmaker import GateStatus, ModelTier, QuestionType, Sourcing
from cellar.schemas.recommendation import (
    ConditionState,
    ContextCondition,
    CultureAction,
    MechanismFit,
    PathwayPartner,
    RecommendationCard,
    ScienceGate,
    ScoreBreakdown,
    ScoredDimension,
    Strength,
)
from cellar.tools.recommend import DIM_LABELS, DIM_PHRASING, FACT_DIMS, make_card, render_card_text

_TIER_LABELS: dict[ModelTier, str] = {
    ModelTier.TWO_D_LINE: "2D cell line",
    ModelTier.ORGANOID: "Organoid",
    ModelTier.COCULTURE: "Co-culture",
    ModelTier.IN_VIVO: "In vivo (GEMM/PDX)",
}

_VERDICT_LABELS: dict[GateStatus, str] = {
    GateStatus.PASSED: "Recommended",
    GateStatus.SCIENCE_GATE_FAILED: "Rejected — science gate",
    GateStatus.MOA_CONTEXT_UNMET: "Rejected — wrong model for this mechanism",
    GateStatus.NO_PROTEIN_EVIDENCE: "Rejected — no protein evidence",
    GateStatus.PATHWAY_INCOHERENT: "Rejected — pathway incoherent",
}

_STRONG_MIN = 0.7
_MODERATE_MIN = 0.45
_PRO_MIN = 0.6


def _strength(value: float) -> Strength:
    if value >= _STRONG_MIN:
        return Strength.STRONG
    if value >= _MODERATE_MIN:
        return Strength.MODERATE
    return Strength.WEAK


def _dimension_source(
    key: str,
    *,
    ensembl: str,
    symbol: str,
    pathway_pmids: list[str],
    context_pmids: list[str],
) -> tuple[str, str | None]:
    name = DIM_PHRASING[key]["source"]
    if key == "protein_present" and ensembl:
        return name, f"https://www.proteinatlas.org/{ensembl}"
    if key == "isoform_match" and ensembl:
        return name, f"https://www.ensembl.org/Homo_sapiens/Gene/Summary?g={ensembl}"
    if key == "pathway_coherence" and pathway_pmids:
        return name, f"https://pubmed.ncbi.nlm.nih.gov/{pathway_pmids[0]}/"
    if key == "context_fit" and context_pmids:
        return name, f"https://pubmed.ncbi.nlm.nih.gov/{context_pmids[0]}/"
    if key == "dependency_signal" and symbol:
        return name, f"https://depmap.org/portal/gene/{symbol}"
    return name, None


def _dimensions(
    scores: dict[str, object],
    *,
    ensembl: str,
    symbol: str,
    pathway_pmids: list[str],
    context_pmids: list[str],
) -> list[ScoredDimension]:
    dimensions: list[ScoredDimension] = []
    for key, label in DIM_LABELS.items():
        if key not in scores:
            continue
        value = round(float(scores[key]), 3)
        if key in FACT_DIMS:
            phrasing = DIM_PHRASING[key]
            text = phrasing["pro"] if value >= _PRO_MIN else phrasing["con"]
            source, source_url = _dimension_source(
                key,
                ensembl=ensembl,
                symbol=symbol,
                pathway_pmids=pathway_pmids,
                context_pmids=context_pmids,
            )
            dimensions.append(
                ScoredDimension(
                    key=key,
                    label=text,
                    value=value,
                    strength=_strength(value),
                    source=source,
                    source_url=source_url,
                )
            )
        else:
            dimensions.append(
                ScoredDimension(key=key, label=label, value=value, strength=_strength(value))
            )
    return dimensions


def _science_gate(pathway: dict[str, object] | None) -> ScienceGate | None:
    if not pathway:
        return None
    return ScienceGate(
        verdict=str(pathway.get("verdict", "")),
        coherence=pathway.get("pathway_coherence"),
        partners=[
            PathwayPartner(
                gene=str(member.get("gene", "")),
                relation_type=str(member.get("relation_type", "")),
                gates_model_selection=bool(member.get("gates")),
                status=str(member.get("status", "")),
                evidence_pmids=[str(p) for p in (member.get("evidence_pmids") or [])],
            )
            for member in pathway.get("members", [])
        ],
    )


def _mechanism(mechanism: dict[str, object] | None) -> MechanismFit | None:
    if not mechanism:
        return None
    return MechanismFit(
        verdict=str(mechanism.get("verdict", "")),
        context_fit=mechanism.get("context_fit"),
        context_required_unmet=bool(mechanism.get("context_required_unmet")),
        conditions=[
            ContextCondition(
                condition=str(member.get("condition", "")),
                necessity=str(member.get("necessity", "")),
                state=ConditionState(member.get("state", "unmet")),
                retrofittable=bool(member.get("retrofittable")),
                rationale=str(member.get("rationale", "")),
                readout_hint=str(member.get("readout_hint", "")),
                evidence_pmids=[str(p) for p in (member.get("evidence_pmids") or [])],
            )
            for member in mechanism.get("members", [])
        ],
        actions=[
            CultureAction(
                condition=str(action.get("condition", "")),
                action=str(action.get("action", "")),
                cost=str(action.get("cost", "")),
                necessity=str(action.get("necessity", "")),
                readout_hint=str(action.get("readout_hint", "")),
            )
            for action in mechanism.get("actions", [])
        ],
        verify=[
            f"{item.get('condition', '')}: {item.get('rationale', '')}".strip(": ")
            for item in mechanism.get("verify", [])
        ],
    )


def _headline(
    scores: dict[str, object], gate: GateStatus, tier_label: str, mechanism: MechanismFit | None
) -> str:
    if gate is not GateStatus.PASSED:
        return f"{_VERDICT_LABELS[gate]} — fix the biology before assessing suitability."
    science = float(scores.get("science_score", 0.0) or 0.0)
    technical = float(scores.get("tech_score", 0.0) or 0.0)
    if mechanism and mechanism.actions:
        required = [a for a in mechanism.actions if a.necessity == "required"]
        if required:
            return f"{tier_label} works only with culture augmentation ({required[0].condition})."
    return f"{tier_label} passes the science gate — science {science:.2f}, technical {technical:.2f}."


def _member_pmids(block: dict[str, object] | None) -> list[str]:
    if not block:
        return []
    return [
        str(pmid)
        for member in block.get("members", [])
        for pmid in (member.get("evidence_pmids") or [])
    ]


def build_card(
    rank: int,
    candidate_dict: dict[str, object],
    question: str,
    target_context: dict[str, object],
    isoform_summary: dict[str, object],
    proteomics_summary: dict[str, object],
    pathway: dict[str, object] | None,
    mechanism: dict[str, object] | None,
) -> RecommendationCard:
    scores = candidate_dict["scores"]
    card_dict = make_card(
        candidate_dict, question, target_context, isoform_summary, proteomics_summary,
        pathway, mechanism,
    )
    gate = GateStatus(scores.get("gate", "passed"))
    tier = ModelTier(candidate_dict["tier"])
    tier_label = _TIER_LABELS.get(tier, str(tier))
    pathway_pmids = _member_pmids(pathway)
    context_pmids = _member_pmids(mechanism)
    dimensions = _dimensions(
        scores,
        ensembl=str(target_context.get("target_id") or ""),
        symbol=str(target_context.get("symbol") or ""),
        pathway_pmids=pathway_pmids,
        context_pmids=context_pmids,
    )
    fact_dims = [d for d in dimensions if d.key in FACT_DIMS]
    mechanism_fit = _mechanism(mechanism)
    overall = float(scores.get("total", 0.0) or 0.0)
    return RecommendationCard(
        rank=rank,
        model_name=str(candidate_dict["name"]),
        tier=tier,
        tier_label=tier_label,
        question=QuestionType(question),
        recommended=gate is GateStatus.PASSED,
        gate=gate,
        verdict_label=_VERDICT_LABELS.get(gate, "Rejected"),
        confidence=_strength(overall),
        headline=_headline(scores, gate, tier_label, mechanism_fit),
        scores=ScoreBreakdown(
            overall=overall,
            science=scores.get("science_score"),
            technical=scores.get("tech_score"),
            context=scores.get("context_fit"),
        ),
        reasons=[d for d in fact_dims if d.value >= _PRO_MIN],
        watch_outs=[d for d in fact_dims if d.value < _PRO_MIN],
        dimensions=dimensions,
        context_notes=[str(note) for note in card_dict.get("context_for_decision", [])],
        science_gate=_science_gate(pathway),
        mechanism=mechanism_fit,
        sourcing=Sourcing(
            supplier_or_cro=str(candidate_dict.get("source", "")),
            catalog_url=str(candidate_dict.get("catalog_url", "")),
        ),
        rendered_markdown=render_card_text(card_dict),
    )
