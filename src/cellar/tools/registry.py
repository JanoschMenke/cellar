from cellar.tools.base import Tool
from cellar.tools.cell_models import CellModelGeneMutationsTool, FindCellModelTool
from cellar.tools.dependency import GeneDependencyTool
from cellar.tools.lookups import IsoformRiskTool, PathwayRelationsTool, ProteinEvidenceTool
from cellar.tools.recommend_models import RecommendModelsTool


def build_matchmaker_tools() -> list[Tool]:
    return [
        RecommendModelsTool(),
        IsoformRiskTool(),
        ProteinEvidenceTool(),
        PathwayRelationsTool(),
        FindCellModelTool(),
        CellModelGeneMutationsTool(),
        GeneDependencyTool(),
    ]
