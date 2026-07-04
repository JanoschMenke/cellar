import json

from cellar.schemas.matchmaker import MatchmakerQuery, MatchmakerResult, QuestionType
from cellar.services.matchmaker import UnsupportedTargetError, run_matchmaker
from cellar.tools.base import Tool, ToolResult


def _compact(result: MatchmakerResult) -> dict[str, object]:
    return {
        "verdict": result.verdict,
        "in_vivo_recommended": result.in_vivo_recommended,
        "facts": {
            "ot_direct_association": result.facts.ot_direct_association,
            "small_molecule_tractable": result.facts.small_molecule_tractable,
            "n_sourceable_models": result.facts.n_sourceable_models,
            "n_problematic_models": result.facts.n_problematic_models,
            "mrna_protein_discordant": result.facts.mrna_protein_discordant,
            "protein_present": result.facts.protein_present,
            "ms_absence_guard_applied": result.facts.ms_absence_guard_applied,
            "isoform_specificity_risk": result.facts.isoform_specificity_risk,
            "proteomics_modality_note": result.facts.proteomics_modality_note,
        },
        "ranked": [
            {
                "model": card.model_name,
                "tier": str(card.tier),
                "overall_score": card.overall_score,
                "science_score": card.science_score,
                "tech_score": card.tech_score,
                "gate": str(card.gate),
                "recommendation_strength": card.recommendation_strength,
                "top_reasons": card.why_this_model[:2],
                "top_watch_outs": card.watch_outs[:2],
                "sourcing": card.sourcing.supplier_or_cro,
            }
            for card in result.cards
        ],
    }


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
        return ToolResult(content=json.dumps(_compact(result)))
