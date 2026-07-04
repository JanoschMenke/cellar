from cellar.schemas.matchmaker import MatchmakerQuery, QuestionType
from cellar.services.aggregate import aggregate_recommendations
from cellar.services.evidence_store import EvidenceStore, current_store
from cellar.services.matchmaker import UnsupportedTargetError
from cellar.tools.base import Tool, ToolResult


class BuildRecommendationsTool(Tool):
    name = "build_recommendations"
    evidence_store: EvidenceStore | None = None
    description = (
        "Aggregate ALL evidence gathered so far this conversation into the ranked "
        "recommendation cards. Call this LAST, only after using the source tools to "
        "gather evidence for the target and disease (target_disease_evidence, "
        "protein_evidence/protein_atlas_profile, isoform_risk, pathway_relations, "
        "literature_search) and for the specific candidate cell models you want ranked "
        "(find_cell_model, cell_line_provenance, gene_dependency, cell_model_gene_mutations). "
        "It fuses that evidence deterministically and returns the ranked models with "
        "scores, hard-gate status, reasons, watch-outs, and sourcing. It ranks only the "
        "cell models you actually investigated this conversation; if you have not looked "
        "up any specific models it returns no cards and says so."
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
