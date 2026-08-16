import json

from cellar.schemas.tool_inputs import ProteinAtlasProfileInput
from cellar.schemas.tool_names import TOOL_DESCRIPTIONS, ToolName
from cellar.services.sources import hpa
from cellar.tools.base import Tool, ToolResult


class ProteinAtlasProfileTool(Tool[ProteinAtlasProfileInput]):
    name = ToolName.PROTEIN_ATLAS_PROFILE
    description = TOOL_DESCRIPTIONS[ToolName.PROTEIN_ATLAS_PROFILE]
    input_model = ProteinAtlasProfileInput

    def run(self, arguments: ProteinAtlasProfileInput) -> ToolResult:
        try:
            result = hpa.protein_profile(arguments.target_symbol, disease_hint=arguments.disease)
        except Exception as error:
            return ToolResult(content=f"Human Protein Atlas lookup failed: {error}", is_error=True)
        if isinstance(result, dict) and result.get("ensembl_id"):
            result["reference"] = f"https://www.proteinatlas.org/{result['ensembl_id']}"
        return ToolResult(content=json.dumps(result))
