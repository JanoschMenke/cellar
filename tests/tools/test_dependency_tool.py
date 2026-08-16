from unittest.mock import patch

from cellar.schemas.derivation import GeneEffectMissing
from cellar.tools.dependency import GeneDependencyTool


def test_gene_dependency_valid_dispatch_calls_service() -> None:
    tool = GeneDependencyTool()
    with patch(
        "cellar.tools.dependency.dependency.gene_effect_in_model",
        return_value=GeneEffectMissing(reason="mocked"),
    ) as spy:
        result = tool.dispatch({"gene_symbol": "KRAS", "model": "MIA PaCa-2"})
    spy.assert_called_once_with("KRAS", "MIA PaCa-2")
    assert result.is_error is False


def test_gene_dependency_missing_required_skips_service() -> None:
    tool = GeneDependencyTool()
    with patch("cellar.tools.dependency.dependency.gene_effect_in_model") as spy:
        result = tool.dispatch({"model": "MIA PaCa-2"})
    assert result.is_error is True
    spy.assert_not_called()
