import json

from cellar.schemas.tool_inputs import CellLineProvenanceInput
from cellar.schemas.tool_names import TOOL_DESCRIPTIONS, ToolName
from cellar.services.sources import cellosaurus
from cellar.tools.base import Tool, ToolResult


class CellLineProvenanceTool(Tool[CellLineProvenanceInput]):
    name = ToolName.CELL_LINE_PROVENANCE
    description = TOOL_DESCRIPTIONS[ToolName.CELL_LINE_PROVENANCE]
    input_model = CellLineProvenanceInput

    def run(self, arguments: CellLineProvenanceInput) -> ToolResult:
        name = arguments.name
        try:
            result = cellosaurus.provenance(name)
        except Exception as error:
            return ToolResult(content=f"Cellosaurus lookup failed: {error}", is_error=True)
        if result is None:
            return ToolResult(content=json.dumps({"found": False, "name": name}))
        return ToolResult(content=json.dumps(result))
