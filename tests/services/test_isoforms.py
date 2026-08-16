from unittest.mock import patch

from cellar.schemas.sources import Isoform, IsoformSpecificityRisk
from cellar.services.sources import isoforms

_FAKE_LOOKUP: dict[str, object] = {
    "Transcript": [
        {
            "id": "ENST00000001",
            "biotype": "protein_coding",
            "display_name": "GENE-201",
            "is_canonical": 1,
            "Translation": {"length": 300},
        },
        {
            "id": "ENST00000002",
            "biotype": "protein_coding",
            "display_name": "GENE-202",
            "is_canonical": 0,
            "Translation": {"length": 150},
        },
    ]
}


def test_protein_coding_isoforms_calls_http_get_json_and_maps_result() -> None:
    with patch.object(isoforms.http, "get_json", return_value=_FAKE_LOOKUP) as mock_get_json:
        result = isoforms.protein_coding_isoforms("ENSG00000001")

    mock_get_json.assert_called_once_with(
        f"{isoforms.E}/lookup/id/ENSG00000001?expand=1;content-type=application/json",
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    assert result[0].transcript_id == "ENST00000001"
    assert result[0].is_canonical is True
    assert result[1].transcript_id == "ENST00000002"


def test_isoform_risk_summary_returns_typed_low_risk_summary() -> None:
    coding = [
        Isoform(transcript_id="ENST00000001", name="GENE-201", aa_length=300, is_canonical=True),
        Isoform(transcript_id="ENST00000002", name="GENE-202", aa_length=150, is_canonical=False),
    ]
    summary = isoforms.isoform_risk_summary(coding)
    assert summary.canonical == "GENE-201"
    assert summary.canonical_aa == 300
    assert summary.n_protein_coding == 2
    assert summary.n_alternative == 1
    assert summary.aa_span == (150, 300)
    assert summary.isoform_specificity_risk == IsoformSpecificityRisk.LOW
    assert summary.shortest_isoform is not None
    assert summary.shortest_isoform.transcript_id == "ENST00000002"
