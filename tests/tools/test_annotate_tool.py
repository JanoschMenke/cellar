import json

from cellar.tools.annotate import AnnotateRecommendationsTool


def test_annotate_valid_dispatch_returns_rationales() -> None:
    tool = AnnotateRecommendationsTool()
    result = tool.dispatch({"rationales": [{"model": "PANC-1", "why": "because"}]})
    assert result.is_error is False
    assert json.loads(result.content) == {"rationales": [{"model": "PANC-1", "why": "because"}]}


def test_annotate_missing_why_is_error() -> None:
    tool = AnnotateRecommendationsTool()
    result = tool.dispatch({"rationales": [{"model": "PANC-1"}]})
    assert result.is_error is True
