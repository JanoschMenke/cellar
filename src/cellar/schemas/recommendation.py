from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from cellar.schemas.matchmaker import (
    FactsSummary,
    GateStatus,
    MatchmakerQuery,
    ModelTier,
    QuestionType,
    RelationSummary,
    Sourcing,
)


class Strength(StrEnum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class ConditionState(StrEnum):
    NATIVE = "native"
    RETROFIT = "retrofit"
    UNMET = "unmet"


class ScoreBreakdown(BaseModel):
    overall: float
    science: float | None = None
    technical: float | None = None
    context: float | None = None


class ScoredDimension(BaseModel):
    key: str
    label: str
    value: float
    strength: Strength


class PathwayPartner(BaseModel):
    gene: str
    relation_type: str
    gates_model_selection: bool = False
    status: str = ""
    evidence_pmids: list[str] = Field(default_factory=list)


class ScienceGate(BaseModel):
    verdict: str
    coherence: float | None = None
    partners: list[PathwayPartner] = Field(default_factory=list)


class ContextCondition(BaseModel):
    condition: str
    necessity: str
    state: ConditionState
    retrofittable: bool = False
    rationale: str = ""
    readout_hint: str = ""
    evidence_pmids: list[str] = Field(default_factory=list)


class CultureAction(BaseModel):
    condition: str
    action: str
    cost: str = ""
    necessity: str = ""
    readout_hint: str = ""


class MechanismFit(BaseModel):
    verdict: str
    context_fit: float | None = None
    context_required_unmet: bool = False
    conditions: list[ContextCondition] = Field(default_factory=list)
    actions: list[CultureAction] = Field(default_factory=list)
    verify: list[str] = Field(default_factory=list)


class RecommendationCard(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    rank: int
    model_name: str
    tier: ModelTier
    tier_label: str
    question: QuestionType
    recommended: bool
    gate: GateStatus
    verdict_label: str
    confidence: Strength
    headline: str
    scores: ScoreBreakdown
    reasons: list[ScoredDimension] = Field(default_factory=list)
    watch_outs: list[ScoredDimension] = Field(default_factory=list)
    dimensions: list[ScoredDimension] = Field(default_factory=list)
    context_notes: list[str] = Field(default_factory=list)
    science_gate: ScienceGate | None = None
    mechanism: MechanismFit | None = None
    sourcing: Sourcing = Field(default_factory=Sourcing)
    rendered_markdown: str = ""


class RecommendationReport(BaseModel):
    query: MatchmakerQuery
    verdict: str
    in_vivo_recommended: bool
    facts: FactsSummary
    relations: list[RelationSummary] = Field(default_factory=list)
    cards: list[RecommendationCard] = Field(default_factory=list)
