from unittest.mock import patch

from cellar.tools.open_targets import TargetDiseaseEvidenceTool


def test_target_disease_evidence_valid_dispatch_calls_service() -> None:
    tool = TargetDiseaseEvidenceTool()
    with patch(
        "cellar.tools.open_targets.open_targets.target_disease_association",
        return_value={"found": True},
    ) as spy:
        result = tool.dispatch({"target_symbol": "ZDHHC20", "disease": "pancreatic cancer"})
    spy.assert_called_once_with("ZDHHC20", "pancreatic cancer")
    assert result.is_error is False


def test_target_disease_evidence_missing_required_skips_service() -> None:
    tool = TargetDiseaseEvidenceTool()
    with patch("cellar.tools.open_targets.open_targets.target_disease_association") as spy:
        result = tool.dispatch({"disease": "pancreatic cancer"})
    assert result.is_error is True
    spy.assert_not_called()
