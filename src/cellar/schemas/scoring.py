from cellar.schemas.matchmaker import MsDetectabilityTier, Necessity

QUESTION_TIER_PRIOR: dict[str, dict[str, float]] = {
    "hts_screen": {"2d_line": 1.0, "organoid": 0.5, "coculture": 0.2, "in_vivo": 0.0},
    "target_validation": {"2d_line": 0.7, "organoid": 0.9, "coculture": 0.6, "in_vivo": 0.4},
    "mechanism": {"2d_line": 0.5, "organoid": 0.9, "coculture": 0.8, "in_vivo": 0.6},
    "immune_mechanism": {"2d_line": 0.1, "organoid": 0.6, "coculture": 1.0, "in_vivo": 0.8},
    "efficacy": {"2d_line": 0.3, "organoid": 0.7, "coculture": 0.6, "in_vivo": 1.0},
}

SCIENCE_W = dict(
    protein_present=0.24,
    pathway_coherence=0.20,
    context_fit=0.16,
    isoform_match=0.10,
    disease_features_match=0.18,
    dependency_signal=0.12,
)
TECH_W = dict(
    tier_fit=0.34, genetic_tractable=0.22, provenance_ok=0.22, prior_use=0.14, mrna_expressed=0.08
)

STRONG_MIN = 0.7
MODERATE_MIN = 0.45
PRO_MIN = 0.6

MAX_CANDIDATES = 8
MAX_PARTNERS = 6

TIER_FIT_DEFAULT = 0.5
PROTEIN_GATE_MIN = 0.3
PATHWAY_GATE_MIN = 0.35
GATED_SCORE_CAP = 0.35
SCIENCE_BLEND = 0.65
TECH_BLEND = 0.35
IN_VIVO_MAX = 0.45
ORGANISM_MAX = 0.6

REL_WEIGHT: dict[str, float] = {
    "catalytic_cofactor": 1.0,
    "stabilizer_accessory": 0.6,
    "substrate": 0.6,
    "upstream_driver": 0.5,
    "paralog_related": 0.1,
    "no_direct_functional_link": 0.0,
}
REL_WEIGHT_DEFAULT = 0.3
PRESENCE_MIN = 0.4
COHERENCE_DEFAULT = 0.6
COHERENCE_STRONG = 0.6
COHERENCE_WEAK = 0.4

NECESSITY_WEIGHT: dict[str, float] = {
    Necessity.REQUIRED: 1.0,
    Necessity.ENHANCING: 0.5,
    Necessity.HYPOTHESIS: 0.0,
}
NECESSITY_WEIGHT_DEFAULT = 0.5
CREDIT_NATIVE = 1.0
CREDIT_RETROFIT = 0.8
CONTEXT_FIT_DEFAULT = 1.0

MS_TIER_SIGNAL: dict[MsDetectabilityTier, float] = {
    MsDetectabilityTier.UNDETECTED: 0.0,
    MsDetectabilityTier.LOW: 0.4,
    MsDetectabilityTier.MODERATE: 0.7,
    MsDetectabilityTier.HIGH: 1.0,
}
HPA_SIG_FULL = 1.0
HPA_SIG_PARTIAL = 0.7
HPA_SIG_WEAK = 0.3
MS_LOW_MAX = 5
MS_MODERATE_MAX = 25
DEPMAP_LOW = 0.4
CONF_BASE = 0.4
CONF_PER_SIGNAL = 0.15
CONF_TUMOR_BONUS = 0.2
CONF_GATED_CAP = 0.5
CONF_MAX = 0.95

AGGREGATE_PROTEIN_PRESENT_DEFAULT = 0.6
AGGREGATE_ISOFORM_MATCH_HIGH_RISK = 0.5
AGGREGATE_ISOFORM_MATCH_LOW_RISK = 0.85
AGGREGATE_ISOFORM_MATCH_DEFAULT = 0.7
AGGREGATE_DEPENDENCY_SIGNAL_DEFAULT = 0.5
AGGREGATE_DISEASE_FEATURES_DRIVER = 0.85
AGGREGATE_DISEASE_FEATURES_MUTATED = 0.7
AGGREGATE_DISEASE_FEATURES_NO_MUTATIONS = 0.6
AGGREGATE_DISEASE_FEATURES_DEFAULT = 0.65
AGGREGATE_PRIOR_USE_DIVISOR = 3.0
AGGREGATE_MRNA_EXPRESSED_SEED = 0.6
AGGREGATE_GENETIC_TRACTABLE_AVAILABLE = 0.9
AGGREGATE_GENETIC_TRACTABLE_DEFAULT = 0.6

PROPOSED_TIER_PROFILE: dict[str, dict[str, float]] = {
    "organoid": {
        "mrna_expressed": 0.75,
        "disease_features_match": 0.85,
        "genetic_tractable": 0.65,
        "provenance_ok": 0.9,
    },
    "coculture": {
        "mrna_expressed": 0.7,
        "disease_features_match": 0.85,
        "genetic_tractable": 0.5,
        "provenance_ok": 0.85,
    },
    "in_vivo": {
        "mrna_expressed": 0.8,
        "disease_features_match": 0.9,
        "genetic_tractable": 0.6,
        "provenance_ok": 0.95,
    },
}

DEPENDENCY_SIGNAL_DIVISOR = 2.0
