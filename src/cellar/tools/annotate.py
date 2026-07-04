import json

from cellar.tools.base import Tool, ToolResult


class AnnotateRecommendationsTool(Tool):
    name = "annotate_recommendations"
    description = (
        "Attach a one-sentence rationale to each ranked model, AFTER calling "
        "build_recommendations. Pass a list of {model, why}: 'model' is the exact model "
        "name shown on the recommendation cards, and 'why' is a single plain-language "
        "sentence giving the comparative, mechanistic argument for why that model wins or "
        "falls short — the kind of reasoning you put in your prose. Cite each factual "
        "claim inline with a Markdown link, exactly as you would in the chat. The 'why' "
        "renders as the 'Why this model' line on the matching card. This does not change "
        "the ranking; it only annotates the deterministic cards with your reasoning."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "rationales": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string", "description": "Exact model name from the cards."},
                        "why": {"type": "string", "description": "One sentence, with inline Markdown citations."},
                    },
                    "required": ["model", "why"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["rationales"],
        "additionalProperties": False,
    }

    def run(self, arguments: dict[str, object]) -> ToolResult:
        rationales = arguments.get("rationales") or []
        clean = [
            {"model": str(item.get("model", "")), "why": str(item.get("why", ""))}
            for item in rationales
            if isinstance(item, dict) and item.get("model") and item.get("why")
        ]
        return ToolResult(content=json.dumps({"rationales": clean}))
