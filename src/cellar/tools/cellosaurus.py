import json

from cellar.services import cellosaurus
from cellar.tools.base import Tool, ToolResult


class CellLineProvenanceTool(Tool):
    name = "cell_line_provenance"
    description = (
        "Look up a cell line in Cellosaurus for identity, provenance/reliability and "
        "sourcing. Given a cell line name, returns its stable CVCL accession and "
        "synonyms, whether it is a PROBLEMATIC line (misidentified / contaminated / "
        "wrong species) with the reason, supplier catalogue numbers for sourcing "
        "(ATCC / ECACC / DSMZ / …), and cross-reference IDs into other databases "
        "(Cell Model Passports SIDM, DepMap ACH). Use this to check a model is "
        "authentic before recommending it, to get a sourcing lead, or to resolve a "
        "name to the SIDM id needed by the Cell Model Passports and dependency tools."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Cell line name, e.g. 'PANC-1' or 'MIA PaCa-2'.",
            }
        },
        "required": ["name"],
        "additionalProperties": False,
    }

    def run(self, arguments: dict[str, object]) -> ToolResult:
        name = arguments.get("name")
        if not isinstance(name, str) or not name.strip():
            return ToolResult(content="Expected a non-empty string argument 'name'.", is_error=True)
        try:
            result = cellosaurus.provenance(name)
        except Exception as error:
            return ToolResult(content=f"Cellosaurus lookup failed: {error}", is_error=True)
        if result is None:
            return ToolResult(content=json.dumps({"found": False, "name": name}))
        return ToolResult(content=json.dumps(result))
