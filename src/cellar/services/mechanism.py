"""
Mechanism -> model-context layer.

The missing axis: a target's MECHANISM OF ACTION imposes CONTEXT REQUIREMENTS on
the model. A model can express the target, carry the right isoform and have a
coherent pathway, yet still be the WRONG model because the mechanism (and its
readout) is invisible under that model's culture conditions.

Two failure modes this layer catches that the pathway gate and tier prior miss:

  1. RETROFITTABLE context  — the mechanism only fires under a condition you can
     ADD to the media/culture. Example (ZDHHC20): the enzyme palmitoylates the
     EGFR C-tail to tune RTK signalling (PMID 27153536). In unstimulated,
     serum-starved 2D culture there is little EGFR flux to modulate — the readout
     is muted until you add EGF ligand. A good 2D line is still usable, but ONLY
     with the stimulation protocol. The tool must SURFACE that as a culture note,
     not silently pass the model.

  2. NON-RETROFITTABLE context — the mechanism needs a compartment the model does
     not have and cannot cheaply acquire. Example: an immune-evasion mechanism is
     unobservable in a tumour-cell monoculture no matter how well the target is
     expressed; you need a co-culture with immune cells or an immunocompetent
     organism. Here the "good 2D line" is the WRONG model for the question, and
     the layer must GATE it, not merely down-weight it.

So the same target can route to DIFFERENT models depending on WHICH mechanistic
readout the scientist's question is about. This module encodes:
  - a taxonomy of context CONDITIONS (co-culture, ligand, 3D/ECM, hypoxia, ...),
  - what each MODEL can natively provide and what it can RETROFIT,
  - the target's MoA -> required/enhancing conditions (literature-derived, PMIDs),
  - a matcher that turns (model, question) -> context_fit + required-unmet gate +
    the concrete culture ACTIONS to make the mechanism observable.

Design mirrors pathway.py: relations/requirements are DERIVED FROM LITERATURE
(build_moa_context runs in the repl tool with host.mcp/host.llm), cached to JSON,
and consumed deterministically in the python kernel.
"""
import json
import os
import re

# ------------------------------------------------------------------ taxonomy
# The conditions a mechanism can require of a model. Each maps to a capability a
# model either has natively, can retrofit, or cannot provide.
CONTEXT_CONDITIONS = [
    "ligand_stimulation",   # agonist/growth factor added to media (EGF, cytokine)
    "immune_compartment",   # T/NK/myeloid cells present (co-culture or immunocompetent host)
    "tumor_stroma",         # CAFs / ECM / paracrine stromal signalling
    "three_d_architecture", # polarity, gradients, invasion front (organoid/3D/in vivo)
    "hypoxia_metabolic",    # low O2 / nutrient stress / defined metabolic media
    "vascular_flow",        # perfusion / systemic exposure (in vivo, microfluidic)
]

# necessity levels for a requirement, given the scientist's question:
#   required   -> mechanism/readout is INVISIBLE without it. If the model can
#                 neither provide nor retrofit it -> CONTEXT GATE (hard).
#   enhancing  -> improves physiological fidelity / signal window. Confidence modifier.
#   hypothesis -> literature-suggested but unverified for THIS target. Never gates;
#                 emits a "verify" note only.
NECESSITY = ["required", "enhancing", "hypothesis"]

# ------------------------------------------------------------------ model capabilities
# What each model TIER natively provides, and which conditions it can RETROFIT
# (add cheaply without switching to a different model class). Per-instance
# overrides (e.g. an organoid+T-cell co-culture that DOES have an immune
# compartment) are supplied by the caller via model_capabilities().
#   native   : conditions the model provides as-is
#   retrofit : conditions addable in-model, each with the action + rough cost
TIER_CAPABILITIES = {
    "2d_line": {
        "native": set(),
        "retrofit": {
            "ligand_stimulation": ("serum-starve + add recombinant ligand (e.g. EGF)", "trivial"),
            "hypoxia_metabolic":  ("culture in hypoxia chamber / defined low-nutrient media", "low"),
        },
    },
    "organoid": {
        "native": {"three_d_architecture", "tumor_stroma"},
        "retrofit": {
            "ligand_stimulation": ("add recombinant ligand to organoid media", "trivial"),
            "hypoxia_metabolic":  ("hypoxic incubation / metabolic media", "low"),
            "immune_compartment": ("convert to organoid + immune co-culture", "high"),
        },
    },
    "coculture": {
        "native": {"three_d_architecture", "tumor_stroma", "immune_compartment"},
        "retrofit": {
            "ligand_stimulation": ("add recombinant ligand to co-culture media", "trivial"),
            "hypoxia_metabolic":  ("hypoxic incubation", "low"),
        },
    },
    "in_vivo": {
        "native": {"three_d_architecture", "tumor_stroma", "immune_compartment",
                   "vascular_flow"},
        "retrofit": {
            "ligand_stimulation": ("systemic/local agonist dosing (PK-dependent, not equiv. to bath application)", "moderate"),
        },
    },
}

def model_capabilities(tier, overrides=None):
    """Native + retrofittable conditions for a model. `overrides` lets a specific
    instance add/remove capabilities (e.g. a 2D line engineered with a reporter,
    or an organoid explicitly built as an immune co-culture)."""
    base = TIER_CAPABILITIES.get(tier, {"native": set(), "retrofit": {}})
    native = set(base["native"]); retrofit = dict(base["retrofit"])
    if overrides:
        native |= set(overrides.get("add_native", []))
        native -= set(overrides.get("remove_native", []))
        retrofit.update(overrides.get("add_retrofit", {}))
        for k in overrides.get("remove_retrofit", []):
            retrofit.pop(k, None)
    return {"native": native, "retrofit": retrofit}

# ------------------------------------------------------------------ live derivation (repl)
def build_moa_context(target, disease, mcp=None, llm=None, reasoning_model=None,
                      extra_queries=None):
    """Derive the target's MECHANISM -> CONTEXT REQUIREMENTS from literature.
    Runs in the repl tool where host.mcp / host.llm live; pass them in.

    Returns a list of requirement dicts:
      {condition, necessity, applies_to_questions, retrofittable, rationale,
       readout_hint, evidence_pmids, needs_verification}
    Cache to JSON; load with load_moa_context() in the python kernel.

    The LLM is asked, per mechanistic thread in the abstracts, what CULTURE
    CONTEXT is needed to OBSERVE that mechanism — i.e. it converts prose about
    biology into model-selection conditions.
    """
    queries = [f"{target} mechanism {disease}",
               f"{target} palmitoylation signaling",
               f"{target} tumor microenvironment OR immune OR stroma"]
    queries += (extra_queries or [])
    seen, abs_ = set(), []
    for q in queries:
        sr = mcp("pubmed", "search_articles", query=q, max_results=5, sort="relevance")
        pmids = [p for p in sr.get("pmids", []) if p not in seen]
        seen.update(pmids)
        if not pmids:
            continue
        md = mcp("pubmed", "get_article_metadata", pmids=pmids)
        for a in md.get("articles", []):
            ids = a.get("identifiers", {})
            abs_.append({"pmid": str(ids.get("pmid")), "title": a.get("title"),
                         "abstract": (a.get("abstract") or "")[:1100]})
    evidence = "\n".join(f"[PMID {a['pmid']}] {a['title']}\n{a['abstract']}"
                         for a in abs_) or "NO ABSTRACTS FOUND."
    prompt = f"""You are choosing an in-vitro model to study {target} in {disease}.
A model can express {target} yet be USELESS if the mechanism's readout is invisible
under its culture conditions. From the evidence, list the CULTURE-CONTEXT conditions
a model must satisfy to OBSERVE {target}'s mechanism(s).

condition must be one of: {CONTEXT_CONDITIONS}
necessity must be one of: {NECESSITY}
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
    res = llm(prompt, model=reasoning_model) if reasoning_model else llm(prompt)
    m = re.search(r"\[.*\]", res["text"], re.S)
    reqs = json.loads(m.group(0)) if m else []
    return {"target": target, "disease": disease,
            "pmids_scanned": [a["pmid"] for a in abs_], "requirements": reqs}

def load_moa_context(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

# ------------------------------------------------------------------ cached ZDHHC20 MoA context
# Literature-grounded MoA->context requirements for the worked example. The EGFR
# ligand requirement and the invasion/3D requirement are evidence-backed; the
# immune-compartment requirement is a mechanistic HYPOTHESIS for ZDHHC20 (thin
# direct evidence) and is flagged needs_verification so it informs but never
# silently gates without the scientist confirming the mechanistic question.
ZDHHC20_MOA_CONTEXT = {
    "target": "ZDHHC20", "disease": "pancreatic ductal adenocarcinoma",
    "requirements": [
        {
            "condition": "ligand_stimulation", "necessity": "required",
            "applies_to_questions": ["target_validation", "mechanism", "hts_screen", "efficacy"],
            "retrofittable": True,
            "rationale": "ZDHHC20 palmitoylates the EGFR C-terminal tail to tune RTK signalling; "
                         "in unstimulated/serum-starved culture there is little EGFR flux to modulate, "
                         "so the mechanistic readout is muted until ligand is added.",
            "readout_hint": "serum-starve, then EGF-stimulate and read pEGFR/downstream MAPK ± palmitoylation (ABE/acyl-RAC).",
            "evidence_pmids": ["27153536"], "needs_verification": False,
        },
        {
            "condition": "three_d_architecture", "necessity": "required",
            "applies_to_questions": ["mechanism", "efficacy", "immune_mechanism"],
            "retrofittable": False,
            "rationale": "ZDHHC20-dependent phenotypes reported in KRAS-driven PDAC involve invasion/"
                         "metastatic reprogramming, which flat 2D monoculture cannot display.",
            "readout_hint": "invasion front / organoid morphology / in-vivo metastasis; not visible on plastic.",
            "evidence_pmids": ["38821916"], "needs_verification": False,
        },
        {
            "condition": "immune_compartment", "necessity": "required",
            "applies_to_questions": ["immune_mechanism"],
            "retrofittable": False,
            "rationale": "Palmitoylation of immune-checkpoint / antigen-presentation substrates can only "
                         "produce an immune-evasion readout when immune effectors are present.",
            "readout_hint": "T-cell killing / IFN-gamma in tumour+T-cell co-culture or immunocompetent host.",
            "evidence_pmids": [], "needs_verification": True,
        },
        {
            "condition": "hypoxia_metabolic", "necessity": "enhancing",
            "applies_to_questions": ["mechanism", "efficacy"],
            "retrofittable": True,
            "rationale": "Palmitoylation and RTK signalling are metabolically sensitive; hypoxic/nutrient-"
                         "stressed conditions better mimic the PDAC microenvironment.",
            "readout_hint": "repeat key readouts under hypoxia / low-glucose to test robustness.",
            "evidence_pmids": [], "needs_verification": True,
        },
    ],
}

# ------------------------------------------------------------------ the matcher
def requirements_for_question(moa_context, question_type):
    """Select the requirements in play for this question (plus any tagged 'all')."""
    out = []
    for r in moa_context.get("requirements", []):
        aq = r.get("applies_to_questions", ["all"])
        if "all" in aq or question_type in aq:
            out.append(r)
    return out

def match_model_context(tier, moa_context, question_type, capability_overrides=None):
    """Match a model's conditions against the mechanism's context requirements.

    Returns:
      context_fit          0..1 — how well the model can host the mechanism's readout
      context_required_unmet  bool — a REQUIRED, non-retrofittable condition is missing
                                (this is the CONTEXT GATE: right target, wrong model)
      actions              list of concrete culture steps to make the mechanism visible
                                (retrofits the model needs — the contextual evidence
                                 the scientist acts on)
      unmet_required       required conditions the model cannot provide at all
      enhancing_missing    enhancing conditions absent (confidence modifier)
      verify               hypothesis-level conditions to confirm
      members              per-condition detail for the card
    """
    caps = model_capabilities(tier, capability_overrides)
    native, retrofit = caps["native"], caps["retrofit"]
    reqs = requirements_for_question(moa_context, question_type)

    members, actions, unmet_required, enhancing_missing, verify = [], [], [], [], []
    num, den = 0.0, 0.0
    # scoring weight of a satisfied condition by necessity
    w_by = {"required": 1.0, "enhancing": 0.5, "hypothesis": 0.0}
    # credit for HOW a condition is satisfied
    credit_native, credit_retrofit = 1.0, 0.8

    for r in reqs:
        cond = r["condition"]; nec = r.get("necessity", "enhancing")
        is_hyp = (nec == "hypothesis") or r.get("needs_verification")
        w = w_by.get(nec, 0.5)
        pmids = r.get("evidence_pmids") or []
        cite = f"[PMID {','.join(pmids)}]" if pmids else ("[hypothesis — verify]" if is_hyp else "[no direct paper]")

        if cond in native:
            state, credit = "native", credit_native
        elif cond in retrofit:
            action, cost = retrofit[cond]
            state, credit = "retrofit", credit_retrofit
            actions.append({"condition": cond, "action": action, "cost": cost,
                            "necessity": nec, "readout_hint": r.get("readout_hint", ""),
                            "evidence_pmids": pmids})
        else:
            state, credit = "unmet", 0.0
            if nec == "required" and not is_hyp:
                unmet_required.append(cond)
            elif nec == "enhancing":
                enhancing_missing.append(cond)

        if is_hyp and state != "native":
            verify.append({"condition": cond, "rationale": r.get("rationale", "")})

        if w > 0:
            num += w * credit; den += w
        members.append({"condition": cond, "necessity": nec, "state": state,
                        "retrofittable": bool(r.get("retrofittable")),
                        "rationale": r.get("rationale", ""),
                        "readout_hint": r.get("readout_hint", ""),
                        "evidence_pmids": pmids, "cite": cite,
                        "needs_verification": bool(is_hyp)})

    context_fit = round(num / den, 3) if den else 1.0
    context_required_unmet = len(unmet_required) > 0
    if context_required_unmet:
        verdict = ("MECHANISM NOT OBSERVABLE HERE: required context " +
                   "/".join(unmet_required) + f" cannot be provided by a '{tier}' model "
                   "and is not retrofittable — right target, wrong model for this question.")
    elif actions:
        req_actions = [a["condition"] for a in actions if a["necessity"] == "required"]
        if req_actions:
            verdict = ("Mechanism observable ONLY with culture augmentation: " +
                       "; ".join(f"{a['condition']} ({a['action']})" for a in actions
                                 if a["necessity"] == "required") + ".")
        else:
            verdict = "Mechanism observable; optional augmentations available to strengthen the readout."
    else:
        verdict = "Model natively supports the mechanism's context requirements."

    return {"context_fit": context_fit,
            "context_required_unmet": context_required_unmet,
            "actions": actions, "unmet_required": unmet_required,
            "enhancing_missing": enhancing_missing, "verify": verify,
            "members": members, "verdict": verdict,
            "question": question_type, "tier": tier}
