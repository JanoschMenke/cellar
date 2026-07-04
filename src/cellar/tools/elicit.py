import json

from cellar.services import elicit
from cellar.tools.base import Tool, ToolResult


class LiteratureSearchTool(Tool):
    name = "literature_search"
    description = (
        "Semantically search Elicit's corpus of 138M+ academic papers for a research "
        "question or topic. Returns citable papers (title, authors, year, abstract, "
        "DOI/PMID, venue, citation count). Use this when structured databases (Open "
        "Targets, STRING) show weak or absent evidence for a target-disease link but "
        "the primary literature may still be rich, when you need citations to support "
        "a claim, or when checking prior use of a model system for a target/disease."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural-language research question or search query, e.g. 'ZDHHC20 palmitoylation pancreatic cancer'.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of papers to return (default 10).",
            },
            "min_year": {
                "type": "integer",
                "description": "Optional earliest publication year to include.",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def run(self, arguments: dict[str, object]) -> ToolResult:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return ToolResult(content="Expected a non-empty string argument 'query'.", is_error=True)
        max_results = arguments.get("max_results")
        min_year = arguments.get("min_year")
        try:
            result = elicit.search_literature(
                query,
                max_results=int(max_results) if isinstance(max_results, int) else 10,
                min_year=int(min_year) if isinstance(min_year, int) else None,
            )
        except Exception as error:
            return ToolResult(content=f"Elicit literature search failed: {error}", is_error=True)
        return ToolResult(content=json.dumps(result))
