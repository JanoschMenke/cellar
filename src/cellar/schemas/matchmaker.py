from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class QuestionType(StrEnum):
    HTS_SCREEN = "hts_screen"
    TARGET_VALIDATION = "target_validation"
    MECHANISM = "mechanism"
    IMMUNE_MECHANISM = "immune_mechanism"
    EFFICACY = "efficacy"


class ModelTier(StrEnum):
    TWO_D_LINE = "2d_line"
    ORGANOID = "organoid"
    COCULTURE = "coculture"
    IN_VIVO = "in_vivo"


class GateStatus(StrEnum):
    PASSED = "passed"
    SCIENCE_GATE_FAILED = "science_gate_failed"
    MOA_CONTEXT_UNMET = "moa_context_unmet"
    NO_PROTEIN_EVIDENCE = "no_protein_evidence"
    PATHWAY_INCOHERENT = "pathway_incoherent"


class MatchmakerQuery(BaseModel):
    target_symbol: str
    disease: str
    question_type: QuestionType
    constraints: list[str] = Field(default_factory=list)


class RelationSummary(BaseModel):
    gene: str
    relation_type: str
    gates_model_selection: bool
    evidence_pmids: list[str] = Field(default_factory=list)


class Sourcing(BaseModel):
    model_config = ConfigDict(extra="ignore")

    supplier_or_cro: str = ""
    catalog_url: str = ""
    purchasable: bool = False


class PathwayBlock(BaseModel):
    model_config = ConfigDict(extra="ignore")

    verdict: str
    coherence: float | None = None
    members: list[str] = Field(default_factory=list)


class MechanismBlock(BaseModel):
    model_config = ConfigDict(extra="ignore")

    verdict: str
    context_fit: float | None = None
    context_required_unmet: bool | None = None
    conditions: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    verify: list[str] = Field(default_factory=list)


class SeedModel(BaseModel):
    name: str
    tier: ModelTier
    source: str = ""
    catalog_url: str = ""
    mrna_expressed: float = 0.5
    protein_present: float = 0.5
    isoform_match: float = 0.5
    disease_features_match: float = 0.5
    dependency_signal: float = 0.5
    genetic_tractable: float = 0.5
    provenance_ok: float = 1.0
    prior_use: float = 0.0
    coexpression: dict[str, float] = Field(default_factory=dict)
    catalytic_domain_ok: bool = True
    capability_overrides: dict[str, list[str]] | None = None


class DecisionCard(BaseModel):
    model_config = ConfigDict(
        extra="ignore", populate_by_name=True, protected_namespaces=()
    )

    model_name: str = Field(alias="model")
    tier: ModelTier
    overall_score: float
    science_score: float | None = None
    tech_score: float | None = None
    gate: GateStatus
    gate_passed: bool
    recommendation_strength: str
    pathway: PathwayBlock | None = None
    mechanism: MechanismBlock | None = None
    why_this_model: list[str] = Field(default_factory=list)
    watch_outs: list[str] = Field(default_factory=list)
    context_for_decision: list[str] = Field(default_factory=list)
    sourcing: Sourcing = Field(default_factory=Sourcing)
    question_framed: QuestionType
    rendered_text: str = ""


class FactsSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    target_id: str | None = None
    disease_id: str | None = None
    small_molecule_tractable: bool = False
    ot_direct_association: float = 0.0
    n_sourceable_models: int = 0
    n_problematic_models: int = 0
    isoform_n_protein_coding: int = 0
    isoform_aa_span: str = ""
    isoform_specificity_risk: str = ""
    mrna_protein_discordant: bool = False
    protein_present: float = 0.0
    protein_confidence: str = ""
    ms_absence_guard_applied: bool = False
    pride_n_projects: int = 0
    proteomics_modality_note: str = ""
    string_top_partners: list[str] = Field(default_factory=list)


class MatchmakerResult(BaseModel):
    query: MatchmakerQuery
    verdict: str
    in_vivo_recommended: bool
    facts: FactsSummary
    relations: list[RelationSummary] = Field(default_factory=list)
    cards: list[DecisionCard] = Field(default_factory=list)


@dataclass
class ModelCandidate:
    name: str
    tier: str
    source: str = ""
    catalog_url: str = ""
    mrna_expressed: float = 0.5
    protein_present: float = 0.5
    isoform_match: float = 0.5
    pathway_coherence: float = 0.5
    passed_science_gate: bool = True
    context_fit: float = 1.0
    context_required_unmet: bool = False
    disease_features_match: float = 0.5
    dependency_signal: float = 0.5
    genetic_tractable: float = 0.5
    provenance_ok: float = 1.0
    prior_use: float = 0.0
    scores: dict[str, object] = field(default_factory=dict)
