from typing import cast

from cellar.schemas.derivation import MoaContext, PathwayCoherence
from cellar.schemas.labels import DIM_LABELS, DIM_PHRASING, FACT_DIMS, TIER_LABELS, VERDICT_LABELS
from cellar.schemas.matchmaker import (
    GateStatus,
    ModelCandidate,
    ModelTier,
    Necessity,
    QuestionType,
    Sourcing,
)
from cellar.schemas.recommendation import (
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
from cellar.schemas.scoring import MODERATE_MIN, PRO_MIN, STRONG_MIN
from cellar.tools.recommend import render_card_text


def _strength(value: float) -> Strength:
    if value >= STRONG_MIN:
        return Strength.STRONG
    if value >= MODERATE_MIN:
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
        value = round(float(cast("int | float | str", scores[key])), 3)
        if key in FACT_DIMS:
            phrasing = DIM_PHRASING[key]
            text = phrasing["pro"] if value >= PRO_MIN else phrasing["con"]
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


def _science_gate(pathway: PathwayCoherence | None) -> ScienceGate | None:
    if not pathway:
        return None
    return ScienceGate(
        verdict=pathway.verdict,
        coherence=pathway.pathway_coherence,
        partners=[
            PathwayPartner(
                gene=member.gene,
                relation_type=member.relation_type,
                gates_model_selection=member.gates,
                status=str(member.status),
                evidence_pmids=list(member.evidence_pmids),
            )
            for member in pathway.members
        ],
    )


def _mechanism(mechanism: MoaContext | None) -> MechanismFit | None:
    if not mechanism:
        return None
    return MechanismFit(
        verdict=mechanism.verdict,
        context_fit=mechanism.context_fit,
        context_required_unmet=mechanism.context_required_unmet,
        conditions=[
            ContextCondition(
                condition=member.condition,
                necessity=member.necessity,
                state=member.state,
                retrofittable=member.retrofittable,
                rationale=member.rationale,
                readout_hint=member.readout_hint,
                evidence_pmids=list(member.evidence_pmids),
                cite=member.cite,
            )
            for member in mechanism.members
        ],
        actions=[
            CultureAction(
                condition=action.condition,
                action=action.action,
                cost=action.cost,
                necessity=action.necessity,
                readout_hint=action.readout_hint,
            )
            for action in mechanism.actions
        ],
        verify=[f"{item.condition}: {item.rationale}".strip(": ") for item in mechanism.verify],
    )


def _headline(
    scores: dict[str, object], gate: GateStatus, tier_label: str, mechanism: MechanismFit | None
) -> str:
    if gate is not GateStatus.PASSED:
        return f"{VERDICT_LABELS[gate]} — fix the biology before assessing suitability."
    science = float(cast("int | float | str", scores.get("science_score", 0.0) or 0.0))
    technical = float(cast("int | float | str", scores.get("tech_score", 0.0) or 0.0))
    if mechanism and mechanism.actions:
        required = [a for a in mechanism.actions if a.necessity == Necessity.REQUIRED]
        if required:
            return f"{tier_label} works only with culture augmentation ({required[0].condition})."
    return (
        f"{tier_label} passes the science gate — science {science:.2f}, technical {technical:.2f}."
    )


def _member_pmids(block: PathwayCoherence | MoaContext | None) -> list[str]:
    if not block:
        return []
    return [pmid for member in block.members for pmid in member.evidence_pmids]


def _context_notes(
    proteomics_summary: dict[str, object],
    isoform_summary: dict[str, object],
    mechanism: MoaContext | None,
    protein_note: str = "",
) -> list[str]:
    context: list[str] = []
    if proteomics_summary.get("mrna_protein_discordant"):
        context.append(
            "mRNA is broadly expressed but protein is not — do not "
            "rely on RNA-seq alone; confirm protein by WB/IF in your lot."
        )
    if protein_note:
        context.append("Protein evidence: " + protein_note)
    if isoform_summary.get("isoform_specificity_risk") == "high":
        context.append("Isoform caveat: " + str(isoform_summary["message"]))
    disease_protein_prognostic = cast(
        "dict[str, object]", proteomics_summary.get("disease_protein_prognostic") or {}
    )
    for key, value in disease_protein_prognostic.items():
        if isinstance(value, dict) and value.get("is_prognostic"):
            context.append(
                f"Protein-level disease signal: {key.split(' - ')[-1]} "
                f"({value.get('prognostic type', '')})."
            )
    if mechanism:
        for action in mechanism.actions:
            if action.necessity == Necessity.REQUIRED:
                context.append(
                    f"Mechanism needs {action.condition}: {action.action} — {action.readout_hint}"
                )
    return context


def build_card(
    rank: int,
    candidate: ModelCandidate,
    question: str,
    target_context: dict[str, object],
    isoform_summary: dict[str, object],
    proteomics_summary: dict[str, object],
    pathway: PathwayCoherence | None,
    mechanism: MoaContext | None,
    protein_note: str = "",
) -> RecommendationCard:
    assert candidate.scores is not None
    scores = candidate.scores.model_dump()
    gate = GateStatus(str(scores.get("gate", GateStatus.PASSED)))
    tier = ModelTier(candidate.tier)
    tier_label = TIER_LABELS.get(tier, str(tier))
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
    overall = float(cast("int | float | str", scores.get("total", 0.0) or 0.0))
    card = RecommendationCard(
        rank=rank,
        model_name=candidate.name,
        tier=tier,
        tier_label=tier_label,
        question=QuestionType(question),
        recommended=gate is GateStatus.PASSED,
        gate=gate,
        verdict_label=VERDICT_LABELS.get(gate, "Rejected"),
        confidence=_strength(overall),
        headline=_headline(scores, gate, tier_label, mechanism_fit),
        scores=ScoreBreakdown(
            overall=overall,
            science=cast("float | None", scores.get("science_score")),
            technical=cast("float | None", scores.get("tech_score")),
            context=cast("float | None", scores.get("context_fit")),
        ),
        reasons=[d for d in fact_dims if d.value >= PRO_MIN],
        watch_outs=[d for d in fact_dims if d.value < PRO_MIN],
        dimensions=dimensions,
        context_notes=_context_notes(proteomics_summary, isoform_summary, mechanism, protein_note),
        science_gate=_science_gate(pathway),
        mechanism=mechanism_fit,
        sourcing=Sourcing(
            supplier_or_cro=candidate.source,
            catalog_url=candidate.catalog_url,
        ),
    )
    card.rendered_markdown = render_card_text(card, candidate.scores)
    return card
