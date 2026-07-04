import json

from cellar.services import cell_model_passports as cmp
from cellar.tools.base import Tool, ToolResult


class FindCellModelTool(Tool):
    name = "find_cell_model"
    description = (
        "Look up a cancer cell line or organoid in the Wellcome Sanger Cell Model "
        "Passports (the curated hub behind the Sanger Cancer Dependency Map) by name. "
        "Returns its Sanger model id (SIDM), model type, growth properties, which "
        "genomic datasets are available (mutations, expression, proteomics, CRISPR KO, "
        "etc.) and a passport URL. Use it to check whether a named model exists and "
        "what data backs it before recommending it. Tolerates punctuation differences "
        "in the name (e.g. 'MIA PaCa-2' resolves to 'MIA-PaCa-2')."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Cell line or model name, e.g. 'PANC-1' or 'MIA PaCa-2'.",
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
            facts = cmp.model_facts(name)
        except Exception as error:
            return ToolResult(content=f"Cell Model Passports lookup failed: {error}", is_error=True)
        if facts is None:
            return ToolResult(content=json.dumps({"found": False, "name": name}))
        return ToolResult(content=json.dumps({"found": True, **facts}))


class CellModelGeneMutationsTool(Tool):
    name = "cell_model_gene_mutations"
    description = (
        "Get the mutations called in a specific gene for a specific cancer cell model "
        "in Cell Model Passports. Accepts a model name or Sanger SIDM id plus a gene "
        "symbol (e.g. KRAS, TP53). Returns matching mutation records: protein change, "
        "effect, driver status and variant allele fraction. An empty list means no "
        "call for that gene in that model, which is itself informative (the model may "
        "lack mutation data, or be wild-type for that gene)."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "model": {
                "type": "string",
                "description": "Model name (e.g. 'MIA PaCa-2') or SIDM id (e.g. 'SIDM00505').",
            },
            "gene_symbol": {
                "type": "string",
                "description": "HGNC gene symbol, e.g. 'KRAS'.",
            },
        },
        "required": ["model", "gene_symbol"],
        "additionalProperties": False,
    }

    _MUTATION_FIELDS = ("protein", "aa_mut", "effect", "cancer_driver", "vaf", "coding")

    def run(self, arguments: dict[str, object]) -> ToolResult:
        model = arguments.get("model")
        gene_symbol = arguments.get("gene_symbol")
        if not isinstance(model, str) or not isinstance(gene_symbol, str) or not model.strip() or not gene_symbol.strip():
            return ToolResult(content="Expected string arguments 'model' and 'gene_symbol'.", is_error=True)
        try:
            model_names: object = None
            if model.upper().startswith("SIDM"):
                sidm_id: str | None = model
            else:
                found = cmp.find_model(model)
                if found is None:
                    return ToolResult(content=json.dumps({"found": False, "model": model}))
                sidm_id = found["id"]
                model_names = found.get("names")
            result = cmp.model_gene_mutations(sidm_id, gene_symbol)
        except Exception as error:
            return ToolResult(content=f"Cell Model Passports mutation lookup failed: {error}", is_error=True)
        mutations = [
            {field: record.get(field) for field in self._MUTATION_FIELDS}
            for record in result["records"]
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
