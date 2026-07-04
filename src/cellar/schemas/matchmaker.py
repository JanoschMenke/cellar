from dataclasses import dataclass, field
from enum import StrEnum


class ModelTier(StrEnum):
    TWO_D_LINE = "2d_line"
    ORGANOID = "organoid"
    COCULTURE = "coculture"
    IN_VIVO = "in_vivo"


class QuestionType(StrEnum):
    HTS_SCREEN = "hts_screen"
    TARGET_VALIDATION = "target_validation"
    MECHANISM = "mechanism"
    IMMUNE_MECHANISM = "immune_mechanism"
    EFFICACY = "efficacy"


@dataclass
class ModelCandidate:
    name: str
    tier: str                             # a ModelTier value
    source: str = ""                      # ATCC / ECACC / HUB / CRO name
    catalog_url: str = ""
    mrna_expressed: float = 0.5           # from RNA-seq — NOT sufficient on its own
    protein_present: float = 0.5          # from MS/CPTAC/HPA protein — the real gate
    isoform_match: float = 0.5            # expresses the functional (catalytic) isoform
    pathway_coherence: float = 0.5        # cofactor/substrate/upstream co-expressed (science gate)
    passed_science_gate: bool = True      # False if a required cofactor/upstream is absent
    context_fit: float = 1.0              # MoA<->culture-context match (services.mechanism); can the
                                          # mechanism's readout even be OBSERVED in this model
    context_required_unmet: bool = False  # a REQUIRED, non-retrofittable context is missing
                                          # -> right target, wrong model (hard gate)
    disease_features_match: float = 0.5   # carries driver mutations/subtype
    dependency_signal: float = 0.5        # DepMap CRISPR effect of the target
    genetic_tractable: float = 0.5        # can you CRISPR the target here
    provenance_ok: float = 1.0            # 0 if Cellosaurus-flagged problematic
    prior_use: float = 0.0                # from Elicit: used for this target before?
    scores: dict[str, object] = field(default_factory=dict)
