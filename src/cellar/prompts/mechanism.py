def moa_context_prompt(
    target: str,
    disease: str,
    evidence: str,
    context_conditions: list[str],
    necessity: list[str],
) -> str:
    return f"""You are choosing an in-vitro model to study {target} in {disease}.
A model can express {target} yet be USELESS if the mechanism's readout is invisible
under its culture conditions. From the evidence, list the CULTURE-CONTEXT conditions
a model must satisfy to OBSERVE {target}'s mechanism(s).

condition must be one of: {context_conditions}
necessity must be one of: {necessity}
applies_to_questions: subset of [target_validation, mechanism, efficacy,
  immune_mechanism, hts_screen] this condition is needed for (use ["all"] if general).
retrofittable: true if it can be ADDED to a standard culture (e.g. ligand to media),
  false if it needs a different model class (e.g. an immune compartment).
Only cite evidence_pmids that actually support the condition; set needs_verification
true and evidence_pmids [] if you are inferring it without direct evidence for {target}.

EVIDENCE:
{evidence}

Return STRICT JSON: an array of objects with keys condition, necessity,
applies_to_questions, retrofittable, rationale (one sentence), readout_hint
(what assay/readout this unlocks), evidence_pmids, needs_verification."""
