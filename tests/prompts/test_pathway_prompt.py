from cellar.prompts.pathway import relation_map_prompt

_TARGET = "ZDHHC20"
_PARTNER = "GOLGA7"
_ALIASES = ["GOLPH4"]
_EVIDENCE = "[PMID 12345] Some Title\nSome abstract text."
_REL_TYPES = [
    "catalytic_cofactor",
    "stabilizer_accessory",
    "substrate",
    "upstream_driver",
    "paralog_related",
    "no_direct_functional_link",
]

_EXPECTED = f"""Curating a functional-dependency graph for target {_TARGET}.
What is the relationship of {_PARTNER} (aliases: {_ALIASES or "none"}) to {_TARGET}, and would
absence of {_PARTNER} in a cell model abrogate {_TARGET}'s MOLECULAR FUNCTION?

relation_type must be exactly one of: {_REL_TYPES}
Rules:
- If papers describe {_PARTNER} acting on a DIFFERENT enzyme/subfamily than {_TARGET},
  choose no_direct_functional_link for {_TARGET} and name the enzyme it really serves.
- catalytic_cofactor / stabilizer_accessory require DIRECT evidence about {_TARGET}.
- gates_model_selection = true ONLY if absence would make {_TARGET} non-functional.

EVIDENCE:
{_EVIDENCE}

Return STRICT JSON: relation_type, required_for_target_activity (true/false/unknown),
gates_model_selection (bool), consequence_if_absent (one sentence),
evidence_pmids (PMID strings from the evidence that support this),
note (one sentence; name subfamily/mechanism if relevant)."""


def test_relation_map_prompt_matches_expected_text() -> None:
    prompt = relation_map_prompt(
        target=_TARGET,
        partner=_PARTNER,
        aliases=_ALIASES,
        evidence=_EVIDENCE,
        rel_types=_REL_TYPES,
    )

    assert prompt == _EXPECTED


def test_relation_map_prompt_renders_none_for_empty_aliases() -> None:
    prompt = relation_map_prompt(
        target=_TARGET,
        partner=_PARTNER,
        aliases=[],
        evidence=_EVIDENCE,
        rel_types=_REL_TYPES,
    )

    assert "aliases: none" in prompt
