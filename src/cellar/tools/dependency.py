import json

from cellar.schemas.derivation import (
    GeneDependencyMissing,
    GeneDependencyScreened,
    GeneDependencyUnscreened,
    GeneEffectMissing,
    GeneEffectScreened,
    GeneEffectUnscreened,
)
from cellar.schemas.tool_inputs import GeneDependencyInput
from cellar.schemas.tool_names import TOOL_DESCRIPTIONS, ToolName
from cellar.services.derivation import dependency
from cellar.tools.base import Tool, ToolResult

GeneDependencyResult = (
    GeneEffectMissing
    | GeneEffectUnscreened
    | GeneEffectScreened
    | GeneDependencyMissing
    | GeneDependencyUnscreened
    | GeneDependencyScreened
)


class GeneDependencyTool(Tool[GeneDependencyInput]):
    name = ToolName.GENE_DEPENDENCY
    description = TOOL_DESCRIPTIONS[ToolName.GENE_DEPENDENCY]
    input_model = GeneDependencyInput

    def run(self, arguments: GeneDependencyInput) -> ToolResult:
        result: GeneDependencyResult
        try:
            if arguments.model:
                result = dependency.gene_effect_in_model(arguments.gene_symbol, arguments.model)
            else:
                result = dependency.gene_dependency_summary(arguments.gene_symbol)
        except Exception as error:
            return ToolResult(content=f"CRISPR dependency lookup failed: {error}", is_error=True)
        payload = result.model_dump()
        payload["reference"] = f"https://depmap.org/portal/gene/{arguments.gene_symbol}"
        sidm = payload.get("model_id")
        if sidm:
            payload["model_reference"] = f"https://cellmodelpassports.sanger.ac.uk/passports/{sidm}"
        return ToolResult(content=json.dumps(payload))
