import json

from cellar.schemas.tool_inputs import TargetDiseaseEvidenceInput
from cellar.schemas.tool_names import TOOL_DESCRIPTIONS, ToolName
from cellar.services.sources import open_targets
from cellar.tools.base import Tool, ToolResult


class TargetDiseaseEvidenceTool(Tool[TargetDiseaseEvidenceInput]):
    name = ToolName.TARGET_DISEASE_EVIDENCE
    description = TOOL_DESCRIPTIONS[ToolName.TARGET_DISEASE_EVIDENCE]
    input_model = TargetDiseaseEvidenceInput

    def run(self, arguments: TargetDiseaseEvidenceInput) -> ToolResult:
        try:
            if arguments.disease:
                result = open_targets.target_disease_association(
                    arguments.target_symbol, arguments.disease
                )
            else:
                result = open_targets.target_profile(arguments.target_symbol)
        except Exception as error:
            return ToolResult(content=f"Open Targets lookup failed: {error}", is_error=True)
        if isinstance(result, dict) and result.get("ensembl_id"):
            result["reference"] = f"https://platform.opentargets.org/target/{result['ensembl_id']}"
        return ToolResult(content=json.dumps(result))
