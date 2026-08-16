from cellar.schemas.matchmaker import EvidenceTier, Necessity

CRISPR_KO_DATASET = "datasets/crispr_ko"
GENE_EFFECT_FIELD = "fc_clean_qn"
DEPENDENCY_THRESHOLD = -0.5

REL_TYPES = [
    "catalytic_cofactor",
    "stabilizer_accessory",
    "substrate",
    "upstream_driver",
    "paralog_related",
    "no_direct_functional_link",
]

GATING_TYPES = {"catalytic_cofactor", "stabilizer_accessory"}

CONTEXT_CONDITIONS = [
    "ligand_stimulation",
    "immune_compartment",
    "tumor_stroma",
    "three_d_architecture",
    "hypoxia_metabolic",
    "vascular_flow",
]

NECESSITY: list[Necessity] = list(Necessity)

TIER_CAPABILITIES: dict[str, dict[str, object]] = {
    "2d_line": {
        "native": set(),
        "retrofit": {
            "ligand_stimulation": ("serum-starve + add recombinant ligand (e.g. EGF)", "trivial"),
            "hypoxia_metabolic": ("culture in hypoxia chamber / defined low-nutrient media", "low"),
        },
    },
    "organoid": {
        "native": {"three_d_architecture", "tumor_stroma"},
        "retrofit": {
            "ligand_stimulation": ("add recombinant ligand to organoid media", "trivial"),
            "hypoxia_metabolic": ("hypoxic incubation / metabolic media", "low"),
            "immune_compartment": ("convert to organoid + immune co-culture", "high"),
        },
    },
    "coculture": {
        "native": {"three_d_architecture", "tumor_stroma", "immune_compartment"},
        "retrofit": {
            "ligand_stimulation": ("add recombinant ligand to co-culture media", "trivial"),
            "hypoxia_metabolic": ("hypoxic incubation", "low"),
        },
    },
    "in_vivo": {
        "native": {"three_d_architecture", "tumor_stroma", "immune_compartment", "vascular_flow"},
        "retrofit": {
            "ligand_stimulation": (
                "systemic/local agonist dosing (PK-dependent, not equiv. to bath application)",
                "moderate",
            ),
        },
    },
}

SECRETED_HINTS = ("secreted", "extracellular", "blood plasma", "plasma protein")
MEMBRANE_HINTS = (
    "plasma membrane",
    "membrane",
    "vesicle",
    "golgi",
    "er",
    "endoplasmic",
    "mitochond",
    "nucle",
    "cytosol",
    "cytoplasm",
)

TIER_WEIGHT: dict[EvidenceTier, float] = {
    EvidenceTier.MODEL_SPECIFIC: 1.0,
    EvidenceTier.TUMOR_QUANT: 0.9,
    EvidenceTier.LOCALIZATION_AB: 0.6,
    EvidenceTier.MS_DETECTABILITY: 0.4,
}
