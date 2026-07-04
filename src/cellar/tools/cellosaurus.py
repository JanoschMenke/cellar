import json

from cellar.services import cellosaurus
from cellar.tools.base import Tool, ToolResult


class CellLineProvenanceTool(Tool):
    name = "cell_line_provenance"
    description = (
        "Look up a cell line in Cellosaurus for identity, provenance/reliability and "
        "commercial sourcing. Given a cell line name, returns its stable CVCL accession "
        "and synonyms, whether it is a PROBLEMATIC line (misidentified / contaminated / "
        "wrong species) with the reason, direct commercial supplier purchase URLs "
        "(ATCC / ECACC / DSMZ / and ~15 more regional biobanks — a real, clickable "
        "product page, not just a catalogue number), and cross-reference IDs into "
        "other databases (Cell Model Passports SIDM, DepMap ACH). Use this to check a "
        "model is authentic before recommending it, to get a real purchase link for a "
        "standard catalog cell line, or to resolve a name to the SIDM id needed by the "
        "Cell Model Passports and dependency tools. For organoids, co-cultures, GEMM/PDX "
        "or other CRO-built models NOT in a commercial cell-line catalog, this tool "
        "returns found=false — use web_search instead to find current supplier/CRO "
        "sourcing information for those."
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
