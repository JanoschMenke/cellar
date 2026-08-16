import json
from unittest.mock import patch

from cellar.schemas.derivation import HpaProteinEvidence, ProteinSynthesis
from cellar.schemas.sources import IsoformRiskSummary, IsoformSpecificityRisk, StringPartner
from cellar.services.sources import isoforms as isoforms_service
from cellar.services.sources import string_db
from cellar.tools.lookups import IsoformRiskTool, PathwayRelationsTool, ProteinEvidenceTool

_FAKE_HPA_EVIDENCE = HpaProteinEvidence(
    subcellular=[],
    protein_class=None,
    rna_tissue_distribution=None,
    protein_tissue_distribution=None,
    mrna_protein_discordant=False,
    protein_cell_type_intensity=None,
    disease_protein_prognostic={},
)

_FAKE_PROTEIN_SYNTHESIS = ProteinSynthesis(
    protein_present=None,
    confidence=0.0,
    provenance=[],
    caveats=["No protein-level evidence available."],
    ms_absence_guard_applied=False,
    per_tier={},
)

_FAKE_SUMMARY = IsoformRiskSummary(
    canonical="GENE-201",
    canonical_aa=300,
    n_protein_coding=1,
    n_alternative=0,
    aa_span=(300, 300),
    shortest_isoform=None,
    isoform_specificity_risk=IsoformSpecificityRisk.LOW,
    message="The canonical GENE-201 (300 aa) is the only full-length protein-coding isoform.",
)

_FAKE_ENSEMBL_LOOKUP: dict[str, object] = {
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

_EXPECTED_ISOFORM_RISK_JSON = {
    "canonical": "GENE-201",
    "canonical_aa": 300,
    "n_protein_coding": 2,
    "n_alternative": 1,
    "aa_span": [150, 300],
    "shortest_isoform": {
        "name": "GENE-202",
        "transcript_id": "ENST00000002",
        "aa_length": 150,
        "pct_of_canonical": 50,
    },
    "isoform_specificity_risk": "low",
    "message": (
        "Ensembl annotates 2 protein-coding isoforms (150-300 aa), mostly minor/predicted "
        "forms; the canonical GENE-201 (300 aa) is assumed to be the expressed protein. "
        "Isoform choice is treated as low-risk — a firmer call would need the expressed "
        "isoform (junction-level RNA-seq) or a known functional-domain length "
        "(pass functional_len_min)."
    ),
    "reference": "https://www.ensembl.org/Homo_sapiens/Gene/Summary?g=ENSG00000180776",
}


def test_isoform_risk_valid_dispatch_calls_service() -> None:
    tool = IsoformRiskTool()
    with (
        patch(
            "cellar.tools.lookups.open_targets.ot_resolve_target",
            return_value="ENSG00000180776",
        ) as resolve_spy,
        patch("cellar.tools.lookups.isoforms.protein_coding_isoforms", return_value=[]),
        patch("cellar.tools.lookups.isoforms.isoform_risk_summary", return_value=_FAKE_SUMMARY),
    ):
        result = tool.dispatch({"target_symbol": "ZDHHC20"})
    resolve_spy.assert_called_once_with("ZDHHC20")
    assert result.is_error is False
    expected = _FAKE_SUMMARY.model_dump()
    expected["reference"] = "https://www.ensembl.org/Homo_sapiens/Gene/Summary?g=ENSG00000180776"
    assert json.loads(result.content) == json.loads(json.dumps(expected))


def test_isoform_risk_tool_json_matches_pre_refactor_shape() -> None:
    tool = IsoformRiskTool()
    with (
        patch(
            "cellar.tools.lookups.open_targets.ot_resolve_target",
            return_value="ENSG00000180776",
        ),
        patch.object(isoforms_service.http, "get_json", return_value=_FAKE_ENSEMBL_LOOKUP),
    ):
        result = tool.dispatch({"target_symbol": "ZDHHC20"})
    assert result.is_error is False
    assert json.loads(result.content) == _EXPECTED_ISOFORM_RISK_JSON


def test_isoform_risk_missing_required_skips_service() -> None:
    tool = IsoformRiskTool()
    with patch("cellar.tools.lookups.open_targets.ot_resolve_target") as resolve_spy:
        result = tool.dispatch({})
    assert result.is_error is True
    resolve_spy.assert_not_called()


def test_pathway_relations_valid_dispatch_calls_service() -> None:
    tool = PathwayRelationsTool()
    with (
        patch(
            "cellar.tools.lookups.string_db.string_partners",
            return_value=[StringPartner(partner="ZDHHC5", score=0.9)],
        ) as partners_spy,
        patch("cellar.tools.lookups._relations_for", return_value={}),
    ):
        result = tool.dispatch({"target_symbol": "ZDHHC20"})
    partners_spy.assert_called_once_with("ZDHHC20")
    assert result.is_error is False


def test_pathway_relations_tool_json_matches_pre_refactor_shape() -> None:
    tool = PathwayRelationsTool()
    string_payload = [
        {"preferredName_B": "ZDHHC5", "score": 0.912345},
        {"preferredName_B": "LOW", "score": 0.1},
    ]
    with (
        patch.object(string_db.http, "get_json", return_value=string_payload),
        patch("cellar.tools.lookups._relations_for", return_value={}),
    ):
        result = tool.dispatch({"target_symbol": "ZDHHC20"})
    assert result.is_error is False
    assert json.loads(result.content) == {
        "string_partners": [{"partner": "ZDHHC5", "score": 0.912}],
        "literature_relations": {},
    }


def test_pathway_relations_missing_required_skips_service() -> None:
    tool = PathwayRelationsTool()
    with patch("cellar.tools.lookups.string_db.string_partners") as partners_spy:
        result = tool.dispatch({})
    assert result.is_error is True
    partners_spy.assert_not_called()


def test_protein_evidence_valid_dispatch_calls_service() -> None:
    tool = ProteinEvidenceTool()
    with (
        patch(
            "cellar.tools.lookups.open_targets.ot_resolve_target",
            return_value="ENSG00000180776",
        ),
        patch(
            "cellar.tools.lookups.proteomics.hpa_protein_evidence",
            return_value=_FAKE_HPA_EVIDENCE,
        ) as hpa_spy,
        patch("cellar.tools.lookups._pride_for", return_value=None),
        patch("cellar.tools.lookups.proteomics.cptac_tumor_quant", return_value={}),
        patch("cellar.tools.lookups.proteomics.depmap_proteomics", return_value={}),
        patch(
            "cellar.tools.lookups.proteomics.synthesize_protein_evidence",
            return_value=_FAKE_PROTEIN_SYNTHESIS,
        ),
    ):
        result = tool.dispatch({"target_symbol": "ZDHHC20", "disease": "pancreatic cancer"})
    hpa_spy.assert_called_once_with("ENSG00000180776", disease_hint="pancreatic cancer")
    assert result.is_error is False


def test_protein_evidence_missing_required_skips_service() -> None:
    tool = ProteinEvidenceTool()
    with patch("cellar.tools.lookups.proteomics.hpa_protein_evidence") as hpa_spy:
        result = tool.dispatch({"disease": "pancreatic cancer"})
    assert result.is_error is True
    hpa_spy.assert_not_called()
