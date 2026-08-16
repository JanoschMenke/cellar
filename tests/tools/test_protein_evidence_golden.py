import json
from unittest.mock import patch

from cellar.tools.lookups import ProteinEvidenceTool

RAW_PROFILE_SIGNAL: dict[str, object] = {
    "Subcellular location": ["Nucleus", "Cytosol"],
    "Protein class": ["Enzymes"],
    "RNA tissue distribution": "Detected in all",
    "Protein tissue distribution": "Detected in some",
    "Protein cell type specific Intensity": {"pancreas": 12.3, "liver": 5.0},
    "Cancer prognostics - Pancreatic cancer": {
        "is_prognostic": True,
        "prognostic type": "unfavourable",
    },
}

PRIDE_SIGNAL: dict[str, object] = {
    "uniprot": "P12345",
    "n_projects": 30,
    "tier": "high",
    "is_detectable": True,
    "projects": ["PXD001", "PXD002"],
}

RAW_PROFILE_NO_SIGNAL: dict[str, object] = {
    "Subcellular location": ["Plasma membrane"],
    "Protein class": ["Enzymes"],
    "RNA tissue distribution": None,
    "Protein tissue distribution": None,
    "Protein cell type specific Intensity": None,
    "Cancer prognostics - Pancreatic cancer": {
        "is_prognostic": False,
        "prognostic type": "NA",
    },
}

PRIDE_NO_SIGNAL: dict[str, object] = {
    "uniprot": "Q99999",
    "n_projects": 3,
    "tier": "low",
    "is_detectable": True,
    "projects": ["PXD010"],
}

EXPECTED_SIGNAL_JSON: dict[str, object] = {
    "hpa": {
        "subcellular": ["Nucleus", "Cytosol"],
        "protein_class": ["Enzymes"],
        "rna_tissue_distribution": "Detected in all",
        "protein_tissue_distribution": "Detected in some",
        "mrna_protein_discordant": True,
        "protein_cell_type_intensity": {"pancreas": 12.3, "liver": 5.0},
        "disease_protein_prognostic": {
            "Cancer prognostics - Pancreatic cancer": {
                "is_prognostic": True,
                "prognostic type": "unfavourable",
            }
        },
    },
    "pride": {
        "uniprot": "P12345",
        "n_projects": 30,
        "tier": "high",
        "is_detectable": True,
        "projects": ["PXD001", "PXD002"],
    },
    "synthesis": {
        "protein_present": 0.82,
        "confidence": 0.7,
        "provenance": [
            "HPA protein 'Detected in some', subcellular=['Nucleus', 'Cytosol']",
            "PRIDE MS projects n=30 (tier=high)",
        ],
        "caveats": [
            "mRNA broad but protein narrow (HPA) — confirm protein "
            "by WB/IF in your lot; do not rely on RNA-seq."
        ],
        "ms_absence_guard_applied": False,
        "per_tier": {
            "localization_ab": "Detected in some",
            "ms_detectability": {
                "uniprot": "P12345",
                "n_projects": 30,
                "tier": "high",
                "is_detectable": True,
                "projects": ["PXD001", "PXD002"],
            },
        },
        "tiers_used": ["localization_ab", "ms_detectability"],
    },
}

EXPECTED_NO_SIGNAL_JSON: dict[str, object] = {
    "hpa": {
        "subcellular": ["Plasma membrane"],
        "protein_class": ["Enzymes"],
        "rna_tissue_distribution": None,
        "protein_tissue_distribution": None,
        "mrna_protein_discordant": False,
        "protein_cell_type_intensity": None,
        "disease_protein_prognostic": {
            "Cancer prognostics - Pancreatic cancer": {
                "is_prognostic": False,
                "prognostic type": "NA",
            }
        },
    },
    "pride": {
        "uniprot": "Q99999",
        "n_projects": 3,
        "tier": "low",
        "is_detectable": True,
        "projects": ["PXD010"],
    },
    "synthesis": {
        "protein_present": None,
        "confidence": 0.0,
        "provenance": ["PRIDE MS projects n=3 (tier=low)"],
        "caveats": [
            "MS-absence guard: low MS detectability (PRIDE n=3) is expected for a "
            "membrane/low-abundance target and is NOT evidence of absence — weighted "
            "down, not used to reject."
        ],
        "ms_absence_guard_applied": True,
        "per_tier": {
            "ms_detectability": {
                "uniprot": "Q99999",
                "n_projects": 3,
                "tier": "low",
                "is_detectable": True,
                "projects": ["PXD010"],
            }
        },
    },
}


def _run(raw_profile: dict[str, object], pride: dict[str, object] | None) -> str:
    tool = ProteinEvidenceTool()
    with (
        patch(
            "cellar.tools.lookups.open_targets.ot_resolve_target",
            return_value="ENSG00000123456",
        ),
        patch(
            "cellar.services.derivation.proteomics.hpa.raw_profile",
            return_value=raw_profile,
        ),
        patch("cellar.tools.lookups._pride_for", return_value=pride),
    ):
        result = tool.dispatch({"target_symbol": "TESTGENE", "disease": "Pancreatic"})
    assert result.is_error is False, result.content
    return result.content


def test_protein_evidence_tool_json_matches_pre_refactor_shape_signal_branch() -> None:
    content = _run(RAW_PROFILE_SIGNAL, PRIDE_SIGNAL)
    parsed = json.loads(content)
    assert parsed == EXPECTED_SIGNAL_JSON
    assert set(parsed["synthesis"].keys()) == {
        "protein_present",
        "confidence",
        "provenance",
        "caveats",
        "ms_absence_guard_applied",
        "per_tier",
        "tiers_used",
    }


def test_protein_evidence_tool_json_matches_pre_refactor_shape_no_signal_branch() -> None:
    content = _run(RAW_PROFILE_NO_SIGNAL, PRIDE_NO_SIGNAL)
    parsed = json.loads(content)
    assert parsed == EXPECTED_NO_SIGNAL_JSON
    assert set(parsed["synthesis"].keys()) == {
        "protein_present",
        "confidence",
        "provenance",
        "caveats",
        "ms_absence_guard_applied",
        "per_tier",
    }
    assert parsed["synthesis"]["protein_present"] is None
    assert "tiers_used" not in parsed["synthesis"]
