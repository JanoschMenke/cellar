from cellar.tools.base import Tool, ToolResult


class CountCharactersTool(Tool):
    name = "count_characters"
    description = (
        "Count the number of characters in a piece of text. "
        "Use this whenever the user asks how long a string or piece of text is."
    )
    input_schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
        "additionalProperties": False,
    }

    def run(self, arguments: dict[str, object]) -> ToolResult:
        text = arguments.get("text")
        if not isinstance(text, str):
            return ToolResult(content="Expected a string argument named 'text'.", is_error=True)
        return ToolResult(content=str(len(text)))
