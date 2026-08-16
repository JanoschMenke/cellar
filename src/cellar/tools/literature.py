import json

from cellar.schemas.tool_inputs import LiteratureSearchInput
from cellar.schemas.tool_names import TOOL_DESCRIPTIONS, ToolName
from cellar.services.sources import literature
from cellar.tools.base import Tool, ToolResult


class LiteratureSearchTool(Tool[LiteratureSearchInput]):
    name = ToolName.LITERATURE_SEARCH
    description = TOOL_DESCRIPTIONS[ToolName.LITERATURE_SEARCH]
    input_model = LiteratureSearchInput

    def run(self, arguments: LiteratureSearchInput) -> ToolResult:
        try:
            result = literature.search_literature(
                arguments.query,
                max_results=arguments.max_results,
                min_year=arguments.min_year,
            )
        except Exception as error:
            return ToolResult(content=f"Literature search failed: {error}", is_error=True)
        return ToolResult(content=json.dumps(result))
