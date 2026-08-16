from cellar.schemas.derivation import CandidateScores
from cellar.schemas.labels import CONDITION_STATE_LABELS, DIM_LABELS, REJECT_LABELS
from cellar.schemas.matchmaker import GateStatus
from cellar.schemas.recommendation import (
    ContextCondition,
    CultureAction,
    MechanismFit,
    PathwayPartner,
    RecommendationCard,
    ScienceGate,
)
from cellar.schemas.scoring import MODERATE_MIN, STRONG_MIN


def _member_line(partner: PathwayPartner) -> str:
    tag = "GATES" if partner.gates_model_selection else "context"
    cite = (
        f" [PMID {','.join(partner.evidence_pmids)}]"
        if partner.evidence_pmids
        else " [no direct paper]"
    )
    return f"{partner.gene} ({partner.relation_type}, {tag}): {partner.status}{cite}"


def _cond_line(condition: ContextCondition) -> str:
    state = CONDITION_STATE_LABELS.get(condition.state, str(condition.state))
    return (
        f"{condition.condition} ({condition.necessity}, {state}): "
        f"{condition.rationale} {condition.cite}"
    )


def _action_line(action: CultureAction) -> str:
    return f"{action.condition}: {action.action} (cost: {action.cost}) -> unlocks: {action.readout_hint}"


def _science_gate_block(gate: ScienceGate) -> list[str]:
    lines = [f"**STEP 1 — Science gate: {gate.verdict}**"]
    if gate.coherence is not None:
        lines += [f"  pathway coherence = {gate.coherence:.2f}"]
    lines += [f"  · {_member_line(partner)}" for partner in gate.partners] + [""]
    return lines


def _mechanism_block(mechanism: MechanismFit) -> list[str]:
    head = "STEP 1b — Mechanism context"
    if mechanism.context_fit is not None:
        head += f" (fit {mechanism.context_fit:.2f})"
    lines = [f"**{head}: {mechanism.verdict}**"]
    lines += [f"  · {_cond_line(condition)}" for condition in mechanism.conditions]
    if mechanism.actions:
        lines += ["  Culture actions to make the mechanism observable:"]
        lines += [f"    → {_action_line(action)}" for action in mechanism.actions]
    if mechanism.verify:
        lines += [f"    ? verify: {v}" for v in mechanism.verify]
    lines += [""]
    return lines


def _header_strength(card: RecommendationCard) -> str:
    if card.gate is not GateStatus.PASSED:
        return REJECT_LABELS.get(card.gate, "REJECTED — science gate")
    return str(card.confidence)


def render_card_text(card: RecommendationCard, scores: CandidateScores) -> str:
    raw_scores = scores.model_dump()
    pros = [
        f"{DIM_LABELS[k]} ({raw_scores[k]:.2f})"
        for k in DIM_LABELS
        if k in raw_scores and raw_scores[k] >= STRONG_MIN
    ]
    cons = [
        f"{DIM_LABELS[k]} ({raw_scores[k]:.2f})"
        for k in DIM_LABELS
        if k in raw_scores and raw_scores[k] < MODERATE_MIN
    ]
    strength = _header_strength(card)
    lines = [
        f"### {card.model_name}  [{card.tier}]  —  {strength.upper()} "
        f"(overall {card.scores.overall:.2f})",
        f"_Question: {card.question}  |  Science {scores.science_score:.2f} → "
        f"Technical {scores.tech_score:.2f}_",
        "",
    ]
    if card.science_gate:
        lines += _science_gate_block(card.science_gate)
    if card.mechanism:
        lines += _mechanism_block(card.mechanism)
    if card.gate is not GateStatus.PASSED:
        lines += [
            f"**→ NOT RECOMMENDED: {card.gate}. Technical suitability not "
            f"assessed — fix the biology first.**",
            "",
        ]
    lines += ["**STEP 2 — Why this model**"]
    lines += [f"  + {p}" for p in pros]
    lines += ["", "**Watch-outs**"] + [f"  – {c}" for c in (cons or ["No major weak dimensions."])]
    if card.context_notes:
        lines += ["", "**Context for your decision**"] + [f"  • {c}" for c in card.context_notes]
    lines += [
        "",
        f"**Source:** {card.sourcing.supplier_or_cro} {card.sourcing.catalog_url}".rstrip(),
    ]
    return "\n".join(lines)
