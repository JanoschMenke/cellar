import json

from cellar.schemas.tool_inputs import AnnotateRecommendationsInput
from cellar.schemas.tool_names import TOOL_DESCRIPTIONS, ToolName
from cellar.tools.base import Tool, ToolResult


class AnnotateRecommendationsTool(Tool[AnnotateRecommendationsInput]):
    name = ToolName.ANNOTATE_RECOMMENDATIONS
    description = TOOL_DESCRIPTIONS[ToolName.ANNOTATE_RECOMMENDATIONS]
    input_model = AnnotateRecommendationsInput

    def run(self, arguments: AnnotateRecommendationsInput) -> ToolResult:
        clean = [
            {"model": rationale.model, "why": rationale.why}
            for rationale in arguments.rationales
            if rationale.model and rationale.why
        ]
        return ToolResult(content=json.dumps({"rationales": clean}))
