import json

from cellar.services import hpa
from cellar.tools.base import Tool, ToolResult


class ProteinAtlasProfileTool(Tool):
    name = "protein_atlas_profile"
    description = (
        "Look up a target's protein-level profile in the Human Protein Atlas (HPA): "
        "subcellular localization, protein class, tissue/cell-type expression "
        "distribution, antibody reliability, and cancer prognostic significance. "
        "Flags mRNA-vs-protein DISCORDANCE (RNA broadly detected but protein "
        "narrowly detected) — a warning against trusting RNA-seq alone as a "
        "presence proxy. Give a target gene symbol; optionally a disease name to "
        "filter the cancer prognostic results to that tumour type (TCGA + "
        "validation cohorts, with p-values). Use this to check whether a target's "
        "protein is actually detected (not just its mRNA) and where."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "target_symbol": {
                "type": "string",
                "description": "HGNC gene symbol of the target, e.g. 'ZDHHC20'.",
            },
            "disease": {
                "type": "string",
                "description": "Optional disease/tumour type to filter cancer prognostics, e.g. 'Pancreatic'.",
            },
        },
        "required": ["target_symbol"],
        "additionalProperties": False,
    }

    def run(self, arguments: dict[str, object]) -> ToolResult:
        target_symbol = arguments.get("target_symbol")
        disease = arguments.get("disease")
        if not isinstance(target_symbol, str) or not target_symbol.strip():
            return ToolResult(content="Expected a non-empty string argument 'target_symbol'.", is_error=True)
        try:
            result = hpa.protein_profile(
                target_symbol, disease_hint=disease if isinstance(disease, str) and disease.strip() else None
            )
        except Exception as error:
            return ToolResult(content=f"Human Protein Atlas lookup failed: {error}", is_error=True)
        return ToolResult(content=json.dumps(result))
