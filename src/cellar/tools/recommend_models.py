import json

from cellar.schemas.matchmaker import MatchmakerQuery, QuestionType
from cellar.schemas.recommendation import RecommendationReport
from cellar.services.matchmaker import UnsupportedTargetError, run_matchmaker
from cellar.tools.base import Tool, ToolResult


def _payload(result: RecommendationReport) -> dict[str, object]:
    return result.model_dump(
        mode="json",
        exclude={"cards": {"__all__": {"rendered_markdown", "dimensions"}}},
    )


class RecommendModelsTool(Tool):
    name = "recommend_models"
    description = (
        "Rank in-vitro / in-vivo biological models for testing a target in a disease, "
        "given the scientist's question. Runs the deterministic two-stage science-then-"
        "technical pipeline and returns ranked models with scores, hard-gate status, "
        "reasons, watch-outs, and sourcing. Call this for any 'which model should I use "
        "for <target> in <disease>' request."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "target_symbol": {"type": "string", "description": "HGNC gene symbol, e.g. ZDHHC20"},
            "disease": {"type": "string", "description": "Disease name, e.g. pancreatic ductal adenocarcinoma"},
            "question_type": {
                "type": "string",
                "enum": [q.value for q in QuestionType],
                "description": "The experimental intent driving model choice",
            },
        },
        "required": ["target_symbol", "disease", "question_type"],
        "additionalProperties": False,
    }

    def run(self, arguments: dict[str, object]) -> ToolResult:
        try:
            query = MatchmakerQuery.model_validate(arguments)
        except Exception as error:
            return ToolResult(content=f"Invalid query: {error}", is_error=True)
        try:
            result = run_matchmaker(query)
        except UnsupportedTargetError as error:
            return ToolResult(content=str(error), is_error=True)
        return ToolResult(content=json.dumps(_payload(result)))
