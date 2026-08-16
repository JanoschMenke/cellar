from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class OtDiseaseHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str


class OtTractabilityRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modality: str
    label: str
    value: bool


class OtTargetProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    tractability: list[OtTractabilityRow]
    top_diseases: list[tuple[str, float]]


class UniprotHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accession: str | None
    protein_existence_level: int | None


class CellModelHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None
    name: str | None
    category: str | None
    problematic: bool


class StringPartner(BaseModel):
    model_config = ConfigDict(extra="forbid")

    partner: str
    score: float


class Isoform(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcript_id: str
    name: str | None
    aa_length: int | None
    is_canonical: bool


class ShortestIsoform(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    transcript_id: str
    aa_length: int
    pct_of_canonical: int | None


class IsoformSpecificityRisk(StrEnum):
    HIGH = "high"
    LOW = "low"


class IsoformRiskSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical: str | None
    canonical_aa: int | None
    n_protein_coding: int
    n_alternative: int
    aa_span: tuple[int | None, int | None]
    shortest_isoform: ShortestIsoform | None
    isoform_specificity_risk: IsoformSpecificityRisk
    message: str


class CommercialListing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accession: str
    url: str


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    found: bool
    accession: str | None
    names: list[str]
    category: str | None
    species: list[str]
    problematic: bool
    problems: list[str]
    cautions: list[str]
    provenance_ok: float
    commercial_listings: dict[str, CommercialListing]
    cross_ids: dict[str, str]
    cellosaurus_url: str | None


class ModelFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sidm_id: str
    names: list[str] | None
    model_type: str | None
    growth_properties: str | None
    ploidy: float | None
    mutations_per_mb: float | None
    crispr_ko_available: bool
    datasets_available: list[str]
    catalog_url: str
