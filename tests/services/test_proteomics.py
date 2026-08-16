from unittest.mock import patch

from cellar.services.derivation import proteomics

_FAKE_HPA: dict[str, object] = {
    "Subcellular location": ["Plasma membrane"],
    "RNA tissue distribution": "Detected in all",
    "Protein tissue distribution": "Detected in some",
    "Protein class": ["Membrane proteins"],
    "Protein cell type specific Intensity": {"A": 1.0},
    "Cancer prognostics Pancreatic cancer": "favourable",
}


def test_hpa_protein_evidence_calls_hpa_raw_profile_and_maps_result() -> None:
    with patch.object(proteomics.hpa, "raw_profile", return_value=_FAKE_HPA) as mock_raw_profile:
        result = proteomics.hpa_protein_evidence("ENSG00000001")

    mock_raw_profile.assert_called_once_with("ENSG00000001", timeout=60)
    assert result.subcellular == ["Plasma membrane"]
    assert result.protein_class == ["Membrane proteins"]
    assert result.rna_tissue_distribution == "Detected in all"
    assert result.protein_tissue_distribution == "Detected in some"
    assert result.mrna_protein_discordant is True
