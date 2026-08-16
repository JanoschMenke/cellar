from pydantic import BaseModel, ConfigDict, Field

from cellar.schemas.tool_names import ToolName
from cellar.tools.base import Tool, ToolResult


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n: int = Field(ge=0)


class _TypedTool(Tool[_Args]):
    name = ToolName.COUNT_CHARACTERS
    description = "d"
    input_model = _Args

    def run(self, arguments: _Args) -> ToolResult:
        return ToolResult(content=str(arguments.n))


def test_typed_tool_dispatch_validates_and_runs() -> None:
    assert _TypedTool().dispatch({"n": 5}).content == "5"


def test_typed_tool_dispatch_rejects_invalid() -> None:
    result = _TypedTool().dispatch({"n": -1})
    assert result.is_error is True


def test_typed_tool_schema_from_model() -> None:
    assert _TypedTool().to_api_schema()["input_schema"]["additionalProperties"] is False
