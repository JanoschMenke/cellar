from unittest.mock import patch

from cellar.tools.hpa import ProteinAtlasProfileTool


def test_protein_atlas_profile_valid_dispatch_calls_service() -> None:
    tool = ProteinAtlasProfileTool()
    with patch(
        "cellar.tools.hpa.hpa.protein_profile",
        return_value={"found": True},
    ) as spy:
        result = tool.dispatch({"target_symbol": "ZDHHC20", "disease": "Pancreatic"})
    spy.assert_called_once_with("ZDHHC20", disease_hint="Pancreatic")
    assert result.is_error is False


def test_protein_atlas_profile_missing_required_skips_service() -> None:
    tool = ProteinAtlasProfileTool()
    with patch("cellar.tools.hpa.hpa.protein_profile") as spy:
        result = tool.dispatch({"disease": "Pancreatic"})
    assert result.is_error is True
    spy.assert_not_called()
