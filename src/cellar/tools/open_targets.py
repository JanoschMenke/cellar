import json

from cellar.services import open_targets
from cellar.tools.base import Tool, ToolResult


class TargetDiseaseEvidenceTool(Tool):
    name = "target_disease_evidence"
    description = (
        "Query Open Targets for the database 'outside view' on a target. Give a target "
        "gene symbol; optionally give a disease. WITH a disease, returns the overall "
        "target-disease association score, its per-evidence-type breakdown (genetic, "
        "known drug, literature, rna_expression, …) and the target's tractability — a "
        "low score together with small-molecule tractability flags a target the "
        "databases UNDERRATE (worth rescuing via functional data). WITHOUT a disease, "
        "returns tractability plus the target's top associated diseases. Use this to "
        "judge whether the naive association evidence supports the target."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "target_symbol": {
                "type": "string",
                "description": "HGNC gene symbol of the target, e.g. 'ZDHHC20' or 'KRAS'.",
            },
            "disease": {
                "type": "string",
                "description": "Optional disease name, e.g. 'pancreatic ductal adenocarcinoma'. Omit for a target profile.",
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
            if isinstance(disease, str) and disease.strip():
                result = open_targets.target_disease_association(target_symbol, disease)
            else:
                result = open_targets.target_profile(target_symbol)
        except Exception as error:
            return ToolResult(content=f"Open Targets lookup failed: {error}", is_error=True)
        if isinstance(result, dict) and result.get("ensembl_id"):
            result["reference"] = f"https://platform.opentargets.org/target/{result['ensembl_id']}"
        return ToolResult(content=json.dumps(result))
