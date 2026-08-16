from cellar.schemas.tool_inputs import CountCharactersInput
from cellar.schemas.tool_names import TOOL_DESCRIPTIONS, ToolName
from cellar.tools.base import Tool, ToolResult


class CountCharactersTool(Tool[CountCharactersInput]):
    name = ToolName.COUNT_CHARACTERS
    include_in_agent = False
    description = TOOL_DESCRIPTIONS[ToolName.COUNT_CHARACTERS]
    input_model = CountCharactersInput

    def run(self, arguments: CountCharactersInput) -> ToolResult:
        return ToolResult(content=str(len(arguments.text)))
