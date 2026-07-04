"""
Recommendation card generator — the part the scientist actually reads.
Turns scores + evidence into an explicit pros / cons / context / sourcing card,
so the output is a DECISION AID, not a leaderboard. The LLM judge (judge.py)
can rewrite the prose, but this guarantees every dimension is surfaced even
without an LLM.
"""

SCIENCE_LABELS = {
    "protein_present": "Protein detected (MS/CPTAC)",
    "pathway_coherence": "Pathway relevance (substrate/context co-expressed)",
    "context_fit": "Mechanism observable in this model (MoA context)",
    "isoform_match": "Expresses functional isoform",
    "disease_features_match": "Carries disease drivers",
    "dependency_signal": "Target dependency (DepMap)",
}
TECH_LABELS = {
    "tier_fit": "Fits the biological question",
    "genetic_tractable": "CRISPR-tractable",
    "provenance_ok": "Clean provenance",
    "prior_use": "Prior use in literature",
    "mrna_expressed": "mRNA expressed (supporting)",
}
DIM_LABELS = {**SCIENCE_LABELS, **TECH_LABELS}

def _bucket(v):
    return "strong" if v >= 0.7 else "moderate" if v >= 0.45 else "weak"

def make_card(candidate_dict, question_type, target_context, isoform_summary,
              proteomics_summary, pathway_summary=None, mechanism_summary=None):
    """candidate_dict = asdict(ModelCandidate) after scoring."""
    s = candidate_dict["scores"]
    pros, cons = [], []
    for k, label in DIM_LABELS.items():
        if k not in s:
            continue
        b = _bucket(s[k])
        line = f"{label} ({s[k]:.2f})"
        (pros if b == "strong" else cons if b == "weak" else pros).append(
            (line if b != "weak" else line))
        if b == "weak":
            cons.append(line); pros.pop() if line in pros else None
    # cleaner split
    pros = [f"{DIM_LABELS[k]} ({s[k]:.2f})" for k in DIM_LABELS if k in s and s[k] >= 0.7]
    cons = [f"{DIM_LABELS[k]} ({s[k]:.2f})" for k in DIM_LABELS if k in s and s[k] < 0.45]

    # context lines that don't come from the score vector
    context = []
    if proteomics_summary.get("mrna_protein_discordant"):
        context.append("mRNA is broadly expressed but protein is not — do not "
                       "rely on RNA-seq alone; confirm protein by WB/IF in your lot.")
    mod = proteomics_summary.get("modalities", {})
    if mod.get("note"):
        context.append("Proteomics routing: " + mod["note"])
    if isoform_summary.get("isoform_specificity_risk") == "high":
        context.append("Isoform caveat: " + isoform_summary["message"])
    dp = proteomics_summary.get("disease_protein_prognostic") or {}
    for k, v in dp.items():
        if isinstance(v, dict) and v.get("is_prognostic"):
            context.append(f"Protein-level disease signal: {k.split(' - ')[-1]} "
                          f"({v.get('prognostic type','')}).")

    # Pathway / science-gate is the lead: show per-member co-expression.
    pathway_block = None
    if pathway_summary:
        def _member_line(m):
            tag = "GATES" if m.get("gates") else "context"
            pmids = m.get("evidence_pmids") or []
            cite = f" [PMID {','.join(pmids)}]" if pmids else " [no direct paper]"
            return (f"{m['gene']} ({m.get('relation_type','?')}, {tag}): "
                    f"{m['status']}{cite}")
        pathway_block = {
            "verdict": pathway_summary["verdict"],
            "coherence": pathway_summary.get("pathway_coherence"),
            "members": [_member_line(m) for m in pathway_summary.get("members", [])],
        }

    # MoA -> culture-context block: can the mechanism's readout even be observed
    # here, and what must be ADDED to the culture to make it observable.
    mechanism_block = None
    if mechanism_summary:
        ms = mechanism_summary
        def _cond_line(m):
            state = {"native": "native", "retrofit": "add-to-culture",
                     "unmet": "MISSING"}.get(m["state"], m["state"])
            return (f"{m['condition']} ({m['necessity']}, {state}): "
                    f"{m['rationale']} {m['cite']}")
        mechanism_block = {
            "verdict": ms["verdict"],
            "context_fit": ms.get("context_fit"),
            "context_required_unmet": ms.get("context_required_unmet"),
            "conditions": [_cond_line(m) for m in ms.get("members", [])],
            # the actionable part: concrete culture steps the scientist runs
            "actions": [f"{a['condition']}: {a['action']} (cost: {a['cost']})"
                        f" -> unlocks: {a['readout_hint']}"
                        for a in ms.get("actions", [])],
            "verify": [f"{v['condition']}: {v['rationale']}" for v in ms.get("verify", [])],
        }
        # surface required culture actions as decision context too
        for a in ms.get("actions", []):
            if a["necessity"] == "required":
                context.append(f"Mechanism needs {a['condition']}: {a['action']} "
                               f"— {a['readout_hint']}")

    gate = s.get("gate", "passed")
    _REJECT_LABEL = {
        "science_gate_failed": "REJECTED — science gate",
        "moa_context_unmet":   "REJECTED — wrong model for this mechanism",
        "no_protein_evidence": "REJECTED — no protein evidence",
        "pathway_incoherent":  "REJECTED — pathway incoherent",
    }
    return {
        "model": candidate_dict["name"],
        "mechanism": mechanism_block,
        "tier": candidate_dict["tier"],
        "overall_score": s["total"],
        "science_score": s.get("science_score"),
        "tech_score": s.get("tech_score"),
        "gate": gate,
        "gate_passed": gate == "passed",
        "recommendation_strength": (_REJECT_LABEL.get(gate, "REJECTED — science gate")
                                    if gate != "passed" else _bucket(s["total"])),
        "pathway": pathway_block,
        "why_this_model": pros,
        "watch_outs": cons or ["No major weak dimensions."],
        "context_for_decision": context,
        "sourcing": {
            "supplier_or_cro": candidate_dict.get("source", ""),
            "catalog_url": candidate_dict.get("catalog_url", ""),
        },
        "question_framed": question_type,
    }

def render_card_text(card):
    sci = card.get("science_score"); tech = card.get("tech_score")
    L = [f"### {card['model']}  [{card['tier']}]  —  {card['recommendation_strength'].upper()} "
         f"(overall {card['overall_score']:.2f})",
         f"_Question: {card['question_framed']}  |  Science {sci:.2f} → Technical {tech:.2f}_", ""]
    # Pathway science gate leads.
    if card.get("pathway"):
        p = card["pathway"]
        L += [f"**STEP 1 — Science gate: {p['verdict']}**"]
        if p.get("coherence") is not None:
            L += [f"  pathway coherence = {p['coherence']:.2f}"]
        L += [f"  · {m}" for m in p["members"]] + [""]
    # Mechanism -> culture-context (the "right target, wrong conditions" check).
    if card.get("mechanism"):
        mb = card["mechanism"]
        head = "STEP 1b — Mechanism context"
        if mb.get("context_fit") is not None:
            head += f" (fit {mb['context_fit']:.2f})"
        L += [f"**{head}: {mb['verdict']}**"]
        L += [f"  · {c}" for c in mb["conditions"]]
        if mb["actions"]:
            L += ["  Culture actions to make the mechanism observable:"]
            L += [f"    → {a}" for a in mb["actions"]]
        if mb["verify"]:
            L += [f"    ? verify: {v}" for v in mb["verify"]]
        L += [""]
    if not card["gate_passed"]:
        L += [f"**→ NOT RECOMMENDED: {card['gate']}. Technical suitability not "
              f"assessed — fix the biology first.**", ""]
    L += ["**STEP 2 — Why this model**"]
    L += [f"  + {p}" for p in card["why_this_model"]]
    L += ["", "**Watch-outs**"] + [f"  – {c}" for c in card["watch_outs"]]
    if card["context_for_decision"]:
        L += ["", "**Context for your decision**"] + [f"  • {c}" for c in card["context_for_decision"]]
    src = card["sourcing"]
    L += ["", f"**Source:** {src['supplier_or_cro']} {src['catalog_url']}".rstrip()]
    return "\n".join(L)
