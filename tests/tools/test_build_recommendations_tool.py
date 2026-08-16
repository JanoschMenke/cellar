from unittest.mock import patch

from cellar.tools.build_recommendations import BuildRecommendationsTool


def test_build_recommendations_valid_dispatch_calls_service() -> None:
    tool = BuildRecommendationsTool()
    with patch("cellar.tools.build_recommendations.aggregate_recommendations") as spy:
        spy.return_value.model_dump_json.return_value = "{}"
        result = tool.dispatch(
            {
                "target_symbol": "ZDHHC20",
                "disease": "pancreatic ductal adenocarcinoma",
                "question_type": "target_validation",
            }
        )
    spy.assert_called_once()
    assert result.is_error is False


def test_build_recommendations_missing_required_skips_service() -> None:
    tool = BuildRecommendationsTool()
    with patch("cellar.tools.build_recommendations.aggregate_recommendations") as spy:
        result = tool.dispatch({"target_symbol": "ZDHHC20"})
    assert result.is_error is True
    spy.assert_not_called()
