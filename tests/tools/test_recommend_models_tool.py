from unittest.mock import patch

from cellar.tools.recommend_models import RecommendModelsTool


def test_recommend_models_valid_dispatch_calls_service() -> None:
    tool = RecommendModelsTool()
    with patch("cellar.tools.recommend_models.run_matchmaker") as spy:
        spy.return_value.model_dump.return_value = {}
        result = tool.dispatch(
            {
                "target_symbol": "ZDHHC20",
                "disease": "pancreatic ductal adenocarcinoma",
                "question_type": "target_validation",
            }
        )
    spy.assert_called_once()
    assert result.is_error is False


def test_recommend_models_missing_required_skips_service() -> None:
    tool = RecommendModelsTool()
    with patch("cellar.tools.recommend_models.run_matchmaker") as spy:
        result = tool.dispatch({"target_symbol": "ZDHHC20"})
    assert result.is_error is True
    spy.assert_not_called()


def test_recommend_models_not_included_in_agent() -> None:
    assert RecommendModelsTool.include_in_agent is False
