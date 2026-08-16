import json

from cellar.schemas.matchmaker import MatchmakerQuery
from cellar.schemas.recommendation import RecommendationReport
from cellar.schemas.tool_inputs import MatchmakerRequestInput
from cellar.schemas.tool_names import TOOL_DESCRIPTIONS, ToolName
from cellar.services.derivation.matchmaker import UnsupportedTargetError, run_matchmaker
from cellar.tools.base import Tool, ToolResult


def _payload(result: RecommendationReport) -> dict[str, object]:
    return result.model_dump(
        mode="json",
        exclude={"cards": {"__all__": {"rendered_markdown", "dimensions"}}},
    )


class RecommendModelsTool(Tool[MatchmakerRequestInput]):
    name = ToolName.RECOMMEND_MODELS
    description = TOOL_DESCRIPTIONS[ToolName.RECOMMEND_MODELS]
    input_model = MatchmakerRequestInput
    include_in_agent = False

    def run(self, arguments: MatchmakerRequestInput) -> ToolResult:
        query = MatchmakerQuery(
            target_symbol=arguments.target_symbol,
            disease=arguments.disease,
            question_type=arguments.question_type,
        )
        try:
            result = run_matchmaker(query)
        except UnsupportedTargetError as error:
            return ToolResult(content=str(error), is_error=True)
        return ToolResult(content=json.dumps(_payload(result)))
