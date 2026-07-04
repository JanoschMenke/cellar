import json

from cellar.services import isoforms, pathway, proteomics, retrieval

from cellar.services.matchmaker import _pride_for, _relations_for
from cellar.tools.base import Tool, ToolResult

_TARGET_ONLY_SCHEMA = {
    "type": "object",
    "properties": {
        "target_symbol": {"type": "string", "description": "HGNC gene symbol, e.g. ZDHHC20"}
    },
    "required": ["target_symbol"],
    "additionalProperties": False,
}


def _resolve(target_symbol: str) -> str | None:
    try:
        return retrieval.ot_resolve_target(target_symbol)
    except Exception:
        return None


class IsoformRiskTool(Tool):
    name = "isoform_risk"
    description = (
        "Enumerate a target's protein-coding isoforms and flag splicing / isoform-"
        "specificity risk (e.g. truncated forms that may lack the catalytic domain). "
        "Use when the scientist asks whether a model expresses the functional isoform."
    )
    input_schema = _TARGET_ONLY_SCHEMA

    def run(self, arguments: dict[str, object]) -> ToolResult:
        symbol = str(arguments.get("target_symbol", ""))
        target_id = _resolve(symbol)
        if target_id is None:
            return ToolResult(content=f"Could not resolve target: {symbol}", is_error=True)
        try:
            summary = isoforms.isoform_risk_summary(isoforms.protein_coding_isoforms(target_id))
        except Exception as error:
            return ToolResult(content=f"Isoform lookup failed: {error}", is_error=True)
        if isinstance(summary, dict):
            summary["reference"] = f"https://www.ensembl.org/Homo_sapiens/Gene/Summary?g={target_id}"
        return ToolResult(content=json.dumps(summary))


class ProteinEvidenceTool(Tool):
    name = "protein_evidence"
    description = (
        "Synthesize tiered protein-presence evidence for a target (HPA localization/"
        "antibody + PRIDE MS detectability, with the MS-absence guard) and route "
        "proteomics modality (MS vs plasma affinity panels). Use to answer 'is the "
        "protein actually present / detectable', not just mRNA."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "target_symbol": {"type": "string", "description": "HGNC gene symbol, e.g. ZDHHC20"},
            "disease": {"type": "string", "description": "Disease hint for tissue matching"},
        },
        "required": ["target_symbol"],
        "additionalProperties": False,
    }

    def run(self, arguments: dict[str, object]) -> ToolResult:
        symbol = str(arguments.get("target_symbol", ""))
        disease = str(arguments.get("disease", ""))
        target_id = _resolve(symbol)
        if target_id is None:
            return ToolResult(content=f"Could not resolve target: {symbol}", is_error=True)
        try:
            hpa = proteomics.hpa_protein_evidence(target_id, disease_hint=disease)
            pride = _pride_for(symbol)
            evidence = proteomics.synthesize_protein_evidence(
                hpa=hpa,
                pride=pride,
                cptac=proteomics.cptac_tumor_quant(symbol),
                depmap=proteomics.depmap_proteomics(symbol),
            )
        except Exception as error:
            return ToolResult(content=f"Protein evidence lookup failed: {error}", is_error=True)
        return ToolResult(content=json.dumps({"hpa": hpa, "pride": pride, "synthesis": evidence}))


class PathwayRelationsTool(Tool):
    name = "pathway_relations"
    description = (
        "Return STRING functional partners plus the literature-derived relation map "
        "(partner -> relation_type + PMIDs + whether it gates model selection). Use to "
        "explain why a partner does or does not hard-reject a model."
    )
    input_schema = _TARGET_ONLY_SCHEMA

    def run(self, arguments: dict[str, object]) -> ToolResult:
        symbol = str(arguments.get("target_symbol", ""))
        try:
            partners = pathway.string_partners(symbol)
        except Exception:
            partners = []
        relations = _relations_for(symbol)
        return ToolResult(
            content=json.dumps(
                {"string_partners": partners[:10], "literature_relations": relations}
            )
        )
