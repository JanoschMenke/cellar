from cellar.schemas.tool_names import TOOL_DESCRIPTIONS, ToolName

_EXPECTED_NAMES = {
    "literature_search",
    "build_recommendations",
    "annotate_recommendations",
    "target_disease_evidence",
    "protein_atlas_profile",
    "protein_evidence",
    "pathway_relations",
    "isoform_risk",
    "gene_dependency",
    "find_cell_model",
    "cell_model_gene_mutations",
    "cell_line_provenance",
    "propose_model_candidate",
    "recommend_models",
    "count_characters",
}


def test_tool_name_values_cover_every_wire_name() -> None:
    assert {member.value for member in ToolName} == _EXPECTED_NAMES


def test_every_tool_has_a_nonempty_description() -> None:
    assert set(TOOL_DESCRIPTIONS) == set(ToolName)
    assert all(text.strip() for text in TOOL_DESCRIPTIONS.values())
