import json
from typing import cast

from cellar.schemas.tool_inputs import CellModelGeneMutationsInput, FindCellModelInput
from cellar.schemas.tool_names import TOOL_DESCRIPTIONS, ToolName
from cellar.services.sources import cell_model_passports as cmp
from cellar.tools.base import Tool, ToolResult


class FindCellModelTool(Tool[FindCellModelInput]):
    name = ToolName.FIND_CELL_MODEL
    description = TOOL_DESCRIPTIONS[ToolName.FIND_CELL_MODEL]
    input_model = FindCellModelInput

    def run(self, arguments: FindCellModelInput) -> ToolResult:
        name = arguments.name
        try:
            facts = cmp.model_facts(name)
        except Exception as error:
            return ToolResult(content=f"Cell Model Passports lookup failed: {error}", is_error=True)
        if facts is None:
            return ToolResult(content=json.dumps({"found": False, "name": name}))
        return ToolResult(content=json.dumps({"found": True, **facts}))


class CellModelGeneMutationsTool(Tool[CellModelGeneMutationsInput]):
    name = ToolName.CELL_MODEL_GENE_MUTATIONS
    description = TOOL_DESCRIPTIONS[ToolName.CELL_MODEL_GENE_MUTATIONS]
    input_model = CellModelGeneMutationsInput

    _MUTATION_FIELDS = ("protein", "aa_mut", "effect", "cancer_driver", "vaf", "coding")

    def run(self, arguments: CellModelGeneMutationsInput) -> ToolResult:
        model = arguments.model
        gene_symbol = arguments.gene_symbol
        try:
            model_names: object = None
            if model.upper().startswith("SIDM"):
                sidm_id: str = model
            else:
                found = cmp.find_model(model)
                if found is None:
                    return ToolResult(content=json.dumps({"found": False, "model": model}))
                sidm_id = cast(str, found["id"])
                model_names = found.get("names")
            result = cmp.model_gene_mutations(sidm_id, gene_symbol)
        except Exception as error:
            return ToolResult(
                content=f"Cell Model Passports mutation lookup failed: {error}", is_error=True
            )
        mutations = [
            {field: record.get(field) for field in self._MUTATION_FIELDS}
            for record in cast("list[dict[str, object]]", result["records"])
        ]
        return ToolResult(
            content=json.dumps(
                {
                    "found": True,
                    "model_id": sidm_id,
                    "model_names": model_names,
                    "gene_symbol": gene_symbol,
                    "n_mutations": len(mutations),
                    "mutations": mutations,
                }
            )
        )
