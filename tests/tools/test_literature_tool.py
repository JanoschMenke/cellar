from unittest.mock import patch

from cellar.tools.literature import LiteratureSearchTool


def test_literature_valid_dispatch_calls_service() -> None:
    tool = LiteratureSearchTool()
    with patch(
        "cellar.tools.literature.literature.search_literature",
        return_value={"found": True, "query": "q", "n_results": 0, "papers": []},
    ) as spy:
        result = tool.dispatch({"query": "ZDHHC20 PDAC", "max_results": 5})
    spy.assert_called_once_with("ZDHHC20 PDAC", max_results=5, min_year=None)
    assert result.is_error is False


def test_literature_missing_required_skips_service() -> None:
    tool = LiteratureSearchTool()
    with patch("cellar.tools.literature.literature.search_literature") as spy:
        result = tool.dispatch({"max_results": 5})
    assert result.is_error is True
    spy.assert_not_called()


def test_literature_extra_key_rejected() -> None:
    result = LiteratureSearchTool().dispatch({"query": "x", "bogus": 1})
    assert result.is_error is True
