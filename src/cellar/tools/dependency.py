import json

from cellar.services import dependency
from cellar.tools.base import Tool, ToolResult


class GeneDependencyTool(Tool):
    name = "gene_dependency"
    description = (
        "Check whether a target gene is a CRISPR knockout dependency ('is my target "
        "essential here') using the Sanger Cancer Dependency Map / Project Score — the "
        "queryable CRISPR-dependency database equivalent to DepMap. Give a gene symbol; "
        "optionally give a specific cell model (name or SIDM id). With a model, returns "
        "that model's gene-effect score (negative = knockout is lethal = a dependency). "
        "Without a model, returns an across-model summary: in how many screened models "
        "the gene is a dependency and how strong. Use this to judge whether a model is "
        "worth choosing because the target is actually essential in it."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "gene_symbol": {
                "type": "string",
                "description": "HGNC gene symbol of the target, e.g. 'KRAS' or 'ZDHHC20'.",
            },
            "model": {
                "type": "string",
                "description": "Optional cell model name (e.g. 'MIA PaCa-2') or SIDM id. Omit for an across-model summary.",
            },
        },
        "required": ["gene_symbol"],
        "additionalProperties": False,
    }

    def run(self, arguments: dict[str, object]) -> ToolResult:
        gene_symbol = arguments.get("gene_symbol")
        model = arguments.get("model")
        if not isinstance(gene_symbol, str) or not gene_symbol.strip():
            return ToolResult(content="Expected a non-empty string argument 'gene_symbol'.", is_error=True)
        try:
            if isinstance(model, str) and model.strip():
                result = dependency.gene_effect_in_model(gene_symbol, model)
            else:
                result = dependency.gene_dependency_summary(gene_symbol)
        except Exception as error:
            return ToolResult(content=f"CRISPR dependency lookup failed: {error}", is_error=True)
        return ToolResult(content=json.dumps(result))
