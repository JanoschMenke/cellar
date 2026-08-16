from pydantic import BaseModel, ConfigDict, Field

from cellar.schemas.matchmaker import (
    CandidateScores,
    EvidenceTier,
    ModelCandidate,
    PathwayMemberStatus,
)
from cellar.schemas.recommendation import ConditionState

__all__ = [
    "CandidateScores",
    "GeneDependencyMissing",
    "GeneDependencyScreened",
    "GeneDependencyUnscreened",
    "GeneEffectMissing",
    "GeneEffectScreened",
    "GeneEffectUnscreened",
    "HpaProteinEvidence",
    "MoaAction",
    "MoaContext",
    "MoaMember",
    "MoaVerify",
    "PathwayCoherence",
    "PathwayMember",
    "ProteinModalities",
    "ProteinSynthesis",
    "RankResult",
    "StrongestModel",
]


class PathwayMember(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gene: str
    relation_type: str
    gates: bool
    expression: float | None
    status: PathwayMemberStatus
    evidence_pmids: list[str] = Field(default_factory=list)
    note: str


class PathwayCoherence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pathway_coherence: float | None
    passed_science_gate: bool | None
    hard_fail: list[str] = Field(default_factory=list)
    members: list[PathwayMember] = Field(default_factory=list)
    verdict: str


class MoaMember(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition: str
    necessity: str
    state: ConditionState
    retrofittable: bool
    rationale: str
    readout_hint: str
    evidence_pmids: list[str] = Field(default_factory=list)
    cite: str
    needs_verification: bool


class MoaAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition: str
    action: str
    cost: str
    necessity: str
    readout_hint: str
    evidence_pmids: list[str] = Field(default_factory=list)


class MoaVerify(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition: str
    rationale: str


class MoaContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context_fit: float
    context_required_unmet: bool
    actions: list[MoaAction] = Field(default_factory=list)
    unmet_required: list[str] = Field(default_factory=list)
    enhancing_missing: list[str] = Field(default_factory=list)
    verify: list[MoaVerify] = Field(default_factory=list)
    members: list[MoaMember] = Field(default_factory=list)
    verdict: str
    question: str
    tier: str


class RankResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ranked: list[ModelCandidate]
    in_vivo_recommended: bool
    verdict: str


class ProteinModalities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    MS_tissue_tumor: bool
    olink_somascan_plasma: bool
    note: str


class HpaProteinEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subcellular: list[str]
    protein_class: list[str] | None
    rna_tissue_distribution: object | None
    protein_tissue_distribution: object | None
    mrna_protein_discordant: bool
    protein_cell_type_intensity: object | None
    disease_protein_prognostic: dict[str, object]
    modalities: ProteinModalities


class ProteinSynthesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protein_present: float | None
    confidence: float
    provenance: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    ms_absence_guard_applied: bool
    per_tier: dict[EvidenceTier, object] = Field(default_factory=dict)
    tiers_used: list[EvidenceTier] | None = None


class GeneEffectMissing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    found: bool = False
    reason: str


class GeneEffectUnscreened(BaseModel):
    model_config = ConfigDict(extra="forbid")

    found: bool = True
    gene_symbol: str
    gene_id: str
    model_id: str
    model_names: object | None
    n_measurements: int
    screened: bool = False
    note: str


class GeneEffectScreened(BaseModel):
    model_config = ConfigDict(extra="forbid")

    found: bool = True
    gene_symbol: str
    gene_id: str
    model_id: str
    model_names: object | None
    n_measurements: int
    screened: bool = True
    gene_effect: float
    bf_scaled: float | None
    qc_pass: bool
    source: list[str] = Field(default_factory=list)
    is_dependency: bool
    dependency_signal: float | None


class GeneDependencyMissing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    found: bool = False
    reason: str


class GeneDependencyUnscreened(BaseModel):
    model_config = ConfigDict(extra="forbid")

    found: bool = True
    gene_symbol: str
    gene_id: str
    n_models: int
    screened: bool = False
    note: str


class StrongestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str
    gene_effect: float


class GeneDependencyScreened(BaseModel):
    model_config = ConfigDict(extra="forbid")

    found: bool = True
    gene_symbol: str
    gene_id: str
    n_models: int
    screened: bool = True
    truncated: bool
    mean_gene_effect: float
    n_dependent_models: int
    fraction_dependent: float
    strongest: StrongestModel
    dependency_signal: float | None
