def relation_map_prompt(
    target: str,
    partner: str,
    aliases: list[str],
    evidence: str,
    rel_types: list[str],
) -> str:
    return f"""Curating a functional-dependency graph for target {target}.
What is the relationship of {partner} (aliases: {aliases or "none"}) to {target}, and would
absence of {partner} in a cell model abrogate {target}'s MOLECULAR FUNCTION?

relation_type must be exactly one of: {rel_types}
Rules:
- If papers describe {partner} acting on a DIFFERENT enzyme/subfamily than {target},
  choose no_direct_functional_link for {target} and name the enzyme it really serves.
- catalytic_cofactor / stabilizer_accessory require DIRECT evidence about {target}.
- gates_model_selection = true ONLY if absence would make {target} non-functional.

EVIDENCE:
{evidence}

Return STRICT JSON: relation_type, required_for_target_activity (true/false/unknown),
gates_model_selection (bool), consequence_if_absent (one sentence),
evidence_pmids (PMID strings from the evidence that support this),
note (one sentence; name subfamily/mechanism if relevant)."""
