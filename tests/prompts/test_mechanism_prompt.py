from cellar.prompts.mechanism import moa_context_prompt

_TARGET = "ZDHHC20"
_DISEASE = "pancreatic cancer"
_EVIDENCE = "[PMID 12345] Some Title\nSome abstract text."
_CONTEXT_CONDITIONS = [
    "ligand_stimulation",
    "immune_compartment",
    "tumor_stroma",
    "three_d_architecture",
    "hypoxia_metabolic",
    "vascular_flow",
]
_NECESSITY = ["required", "enhancing", "hypothesis"]

_EXPECTED = f"""You are choosing an in-vitro model to study {_TARGET} in {_DISEASE}.
A model can express {_TARGET} yet be USELESS if the mechanism's readout is invisible
under its culture conditions. From the evidence, list the CULTURE-CONTEXT conditions
a model must satisfy to OBSERVE {_TARGET}'s mechanism(s).

condition must be one of: {_CONTEXT_CONDITIONS}
necessity must be one of: {_NECESSITY}
applies_to_questions: subset of [target_validation, mechanism, efficacy,
  immune_mechanism, hts_screen] this condition is needed for (use ["all"] if general).
retrofittable: true if it can be ADDED to a standard culture (e.g. ligand to media),
  false if it needs a different model class (e.g. an immune compartment).
Only cite evidence_pmids that actually support the condition; set needs_verification
true and evidence_pmids [] if you are inferring it without direct evidence for {_TARGET}.

EVIDENCE:
{_EVIDENCE}

Return STRICT JSON: an array of objects with keys condition, necessity,
applies_to_questions, retrofittable, rationale (one sentence), readout_hint
(what assay/readout this unlocks), evidence_pmids, needs_verification."""


def test_moa_context_prompt_matches_expected_text() -> None:
    prompt = moa_context_prompt(
        target=_TARGET,
        disease=_DISEASE,
        evidence=_EVIDENCE,
        context_conditions=_CONTEXT_CONDITIONS,
        necessity=_NECESSITY,
    )

    assert prompt == _EXPECTED
