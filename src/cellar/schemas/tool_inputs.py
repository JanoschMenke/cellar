from pydantic import BaseModel, ConfigDict, Field

from cellar.schemas.matchmaker import QuestionType


class LiteratureSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(
        description="Natural-language research question, e.g. 'ZDHHC20 palmitoylation pancreatic cancer'."
    )
    max_results: int = Field(
        default=10, description="Maximum number of papers to return (default 10)."
    )
    min_year: int | None = Field(
        default=None, description="Optional earliest publication year to include."
    )


class MatchmakerRequestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_symbol: str = Field(description="HGNC gene symbol, e.g. ZDHHC20")
    disease: str = Field(description="Disease name, e.g. pancreatic ductal adenocarcinoma")
    question_type: QuestionType = Field(description="The experimental intent driving model choice")


class Rationale(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = Field(description="Exact model name from the cards.")
    why: str = Field(description="One sentence, with inline Markdown citations.")


class AnnotateRecommendationsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rationales: list[Rationale]


class TargetDiseaseEvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_symbol: str = Field(
        description="HGNC gene symbol of the target, e.g. 'ZDHHC20' or 'KRAS'."
    )
    disease: str | None = Field(
        default=None,
        description="Optional disease name, e.g. 'pancreatic ductal adenocarcinoma'. Omit for a target profile.",
    )


class ProteinAtlasProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_symbol: str = Field(description="HGNC gene symbol of the target, e.g. 'ZDHHC20'.")
    disease: str | None = Field(
        default=None,
        description="Optional disease/tumour type to filter cancer prognostics, e.g. 'Pancreatic'.",
    )


class ProteinEvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_symbol: str = Field(description="HGNC gene symbol, e.g. ZDHHC20")
    disease: str | None = Field(default=None, description="Disease hint for tissue matching")


class TargetOnlyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_symbol: str = Field(description="HGNC gene symbol, e.g. ZDHHC20")


class GeneDependencyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gene_symbol: str = Field(
        description="HGNC gene symbol of the target, e.g. 'KRAS' or 'ZDHHC20'."
    )
    model: str | None = Field(
        default=None,
        description="Optional cell model name (e.g. 'MIA PaCa-2') or SIDM id. Omit for an across-model summary.",
    )


class FindCellModelInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(description="Cell line or model name, e.g. 'PANC-1' or 'MIA PaCa-2'.")


class CellModelGeneMutationsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = Field(description="Model name (e.g. 'MIA PaCa-2') or SIDM id (e.g. 'SIDM00505').")
    gene_symbol: str = Field(description="HGNC gene symbol, e.g. 'KRAS'.")


class CellLineProvenanceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(description="Cell line name, e.g. 'PANC-1' or 'MIA PaCa-2'.")


class CountCharactersInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
