from cellar.schemas.matchmaker import MatchmakerQuery
from cellar.schemas.tool_inputs import MatchmakerRequestInput
from cellar.schemas.tool_names import TOOL_DESCRIPTIONS, ToolName
from cellar.services.derivation.aggregate import aggregate_recommendations
from cellar.services.derivation.matchmaker import UnsupportedTargetError
from cellar.services.evidence_store import EvidenceStore, current_store
from cellar.tools.base import Tool, ToolResult


class BuildRecommendationsTool(Tool[MatchmakerRequestInput]):
    name = ToolName.BUILD_RECOMMENDATIONS
    description = TOOL_DESCRIPTIONS[ToolName.BUILD_RECOMMENDATIONS]
    input_model = MatchmakerRequestInput
    evidence_store: EvidenceStore | None = None

    def run(self, arguments: MatchmakerRequestInput) -> ToolResult:
        query = MatchmakerQuery(
            target_symbol=arguments.target_symbol,
            disease=arguments.disease,
            question_type=arguments.question_type,
        )
        store = self.evidence_store or current_store() or EvidenceStore()
        try:
            report = aggregate_recommendations(store, query)
        except UnsupportedTargetError as error:
            return ToolResult(content=str(error), is_error=True)
        return ToolResult(
            content=report.model_dump_json(
                exclude={"cards": {"__all__": {"rendered_markdown", "dimensions"}}}
            )
        )
