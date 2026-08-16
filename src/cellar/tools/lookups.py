import json

from cellar.schemas.sources import StringPartner
from cellar.schemas.tool_inputs import ProteinEvidenceInput, TargetOnlyInput
from cellar.schemas.tool_names import TOOL_DESCRIPTIONS, ToolName
from cellar.services.derivation import proteomics
from cellar.services.derivation.matchmaker import _pride_for, _relations_for
from cellar.services.sources import isoforms, open_targets, string_db
from cellar.tools.base import Tool, ToolResult


def _resolve(target_symbol: str) -> str | None:
    try:
        return open_targets.ot_resolve_target(target_symbol)
    except Exception:
        return None


class IsoformRiskTool(Tool[TargetOnlyInput]):
    name = ToolName.ISOFORM_RISK
    description = TOOL_DESCRIPTIONS[ToolName.ISOFORM_RISK]
    input_model = TargetOnlyInput

    def run(self, arguments: TargetOnlyInput) -> ToolResult:
        symbol = arguments.target_symbol
        target_id = _resolve(symbol)
        if target_id is None:
            return ToolResult(content=f"Could not resolve target: {symbol}", is_error=True)
        try:
            summary = isoforms.isoform_risk_summary(isoforms.protein_coding_isoforms(target_id))
        except Exception as error:
            return ToolResult(content=f"Isoform lookup failed: {error}", is_error=True)
        summary_dict = summary.model_dump()
        summary_dict["reference"] = (
            f"https://www.ensembl.org/Homo_sapiens/Gene/Summary?g={target_id}"
        )
        return ToolResult(content=json.dumps(summary_dict))


class ProteinEvidenceTool(Tool[ProteinEvidenceInput]):
    name = ToolName.PROTEIN_EVIDENCE
    description = TOOL_DESCRIPTIONS[ToolName.PROTEIN_EVIDENCE]
    input_model = ProteinEvidenceInput

    def run(self, arguments: ProteinEvidenceInput) -> ToolResult:
        symbol = arguments.target_symbol
        disease = arguments.disease or ""
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
        synthesis_data = evidence.model_dump()
        if evidence.tiers_used is None:
            synthesis_data.pop("tiers_used")
        return ToolResult(
            content=json.dumps(
                {"hpa": hpa.model_dump(), "pride": pride, "synthesis": synthesis_data}
            )
        )


class PathwayRelationsTool(Tool[TargetOnlyInput]):
    name = ToolName.PATHWAY_RELATIONS
    description = TOOL_DESCRIPTIONS[ToolName.PATHWAY_RELATIONS]
    input_model = TargetOnlyInput

    def run(self, arguments: TargetOnlyInput) -> ToolResult:
        symbol = arguments.target_symbol
        try:
            partners: list[StringPartner] = string_db.string_partners(symbol)
        except Exception:
            partners = []
        relations = _relations_for(symbol)
        return ToolResult(
            content=json.dumps(
                {
                    "string_partners": [p.model_dump() for p in partners[:10]],
                    "literature_relations": relations,
                }
            )
        )
