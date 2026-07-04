"""
End-to-end demo: ZDHHC20 in PDAC.
Runs the live retrieval, builds a small realistic candidate set, scores it,
and prints the ranked recommendation + in-vivo verdict.

Candidate biology (from the live probe + known PDAC model landscape):
- ZDHHC20 = palmitoyltransferase, KRAS-context dependent in PDAC.
- OT direct assoc score ~0 (teaching case) but SM-tractable enzyme.
- ~333 sourceable PDAC lines; the KRAS-mutant, target-expressing subset is small.
"""
from cellar.services import isoforms, mechanism, pathway, proteomics, retrieval
from cellar.schemas.matchmaker import ModelCandidate
from cellar.tools.recommend import make_card, render_card_text
from cellar.tools.scoring import rank

def build_facts():
    tid = retrieval.ot_resolve_target("ZDHHC20")
    did = retrieval.ot_resolve_disease("pancreatic ductal adenocarcinoma")
    prof = retrieval.ot_target_profile(tid)
    assoc = retrieval.ot_assoc_score(tid, did["id"])
    models = retrieval.cello_models("pancreatic ductal adenocarcinoma")
    iso = isoforms.isoform_risk_summary(isoforms.protein_coding_isoforms(tid))
    pro = proteomics.hpa_protein_evidence(tid, disease_hint="Pancreatic")
    # Tiered protein evidence: HPA (localization/antibody) + PRIDE MS detectability
    # (cached live probe: ZDHHC20 Q5W0Z9 -> 0 MS projects). CPTAC/DepMap are
    # documented wiring points; when cached they dominate the synthesis.
    pride = proteomics.ZDHHC20_PRIDE
    protein_evidence = proteomics.synthesize_protein_evidence(
        hpa=pro, pride=pride,
        cptac=proteomics.cptac_tumor_quant("ZDHHC20"),        # not wired -> ignored
        depmap=proteomics.depmap_proteomics("ZDHHC20"))       # not wired -> ignored
    partners = pathway.string_partners("ZDHHC20")
    # Literature-derived relations (cached; produced live by pathway.build_relation_map
    # in the repl tool from PubMed abstracts). This replaces the old asserted
    # "GOLGA7 = required cofactor" checklist. Key result: none of ZDHHC20's
    # headline partners actually gate model selection.
    relations = pathway.ZDHHC20_RELATIONS
    return {
        "target_id": tid, "disease_id": did["id"],
        "sm_tractable": any(x["modality"] == "SM" for x in prof["tractability"]),
        "ot_direct_assoc": assoc,
        "n_sourceable_models": len(models),
        "n_problematic": sum(m["problematic"] for m in models),
        "isoforms": iso,
        "proteomics": pro,
        "protein_evidence": protein_evidence,
        "pride": pride,
        "string_partners": partners,
        "relations": relations,
    }

# Per-model pathway data. Two parts:
#   coexpr        — presence (0..1) of each literature-derived partner in THIS model
#   catalytic_ok  — does the model express an isoform WITH the intact DHHC domain?
# In the real tool these come from the model's own RNA/protein profile
# (DepMap/HPA/organoid RNA-seq + isoform-resolved quant).
#
# TEACHING POINT (corrected): GOLGA7 is low in PANC-1, but GOLGA7 is NOT a
# functional requirement for ZDHHC20 (it stabilises the DHHC9 subfamily, which
# ZDHHC20 is not part of — literature-derived, see services.pathway.ZDHHC20_RELATIONS).
# So low GOLGA7 must NOT reject PANC-1. What legitimately fails a model is losing
# the enzyme itself: the deliberately-broken case here is a line expressing only a
# truncated ZDHHC20 isoform lacking the catalytic DHHC domain -> hard reject on
# CATALYTIC_DOMAIN, not on a phantom cofactor.
MODEL_COEXPRESSION = {
    "Patient-derived PDAC organoid (HUB/Hubrecht)": {"GOLGA7": 0.8,  "KRAS": 0.9,  "EGFR": 0.7},
    "MIA PaCa-2 (KRAS G12C, 2D)":                   {"GOLGA7": 0.6,  "KRAS": 0.85, "EGFR": 0.5},
    "PANC-1 (KRAS G12D, 2D)":                       {"GOLGA7": 0.1,  "KRAS": 0.8,  "EGFR": 0.45},
    "PDAC organoid + autologous T-cell co-culture": {"GOLGA7": 0.8,  "KRAS": 0.85, "EGFR": 0.7},
    "KPC GEMM (LSL-KrasG12D;Trp53;Pdx1-Cre)":       {"GOLGA7": 0.85, "KRAS": 0.95, "EGFR": 0.75},
    "DHHC-truncated PDAC line (isoform w/o DHHC domain)": {"GOLGA7": 0.8, "KRAS": 0.9, "EGFR": 0.7},
}
# Which models express a catalytically intact ZDHHC20 isoform. The truncated line
# is the scientifically-valid rejection: enzyme present by mRNA, but no DHHC domain.
MODEL_CATALYTIC_OK = {
    "DHHC-truncated PDAC line (isoform w/o DHHC domain)": False,
}

# Small hand-set candidate panel (in the real tool this is auto-built by joining
# Cellosaurus x DepMap KRAS-status x HPA expression). Values are illustrative but
# ordered to reflect real PDAC model biology.
def candidates():
    # protein_present/mrna_expressed/isoform_match illustrative but ordered to
    # reflect real PDAC model biology. Note MIA PaCa-2: high mRNA but we set
    # protein lower to demo the discordance gate.
    return [
        ModelCandidate("Patient-derived PDAC organoid (HUB/Hubrecht)", "organoid",
                       source="HUB Organoids / HCMI", mrna_expressed=0.85,
                       protein_present=0.85, isoform_match=0.8,
                       disease_features_match=0.9, dependency_signal=0.6,
                       genetic_tractable=0.8, provenance_ok=1.0, prior_use=0.7),
        ModelCandidate("MIA PaCa-2 (KRAS G12C, 2D)", "2d_line",
                       source="ATCC CRL-1420", mrna_expressed=0.9,
                       protein_present=0.7, isoform_match=0.7,
                       disease_features_match=0.7, dependency_signal=0.5,
                       genetic_tractable=0.95, provenance_ok=1.0, prior_use=0.5),
        ModelCandidate("PANC-1 (KRAS G12D, 2D)", "2d_line",
                       source="ATCC CRL-1469", mrna_expressed=0.8,
                       protein_present=0.65, isoform_match=0.7,
                       disease_features_match=0.7, dependency_signal=0.45,
                       genetic_tractable=0.95, provenance_ok=1.0, prior_use=0.4),
        ModelCandidate("PDAC organoid + autologous T-cell co-culture", "coculture",
                       source="CRO-built (e.g. Crown Bio / Xilis)", mrna_expressed=0.85,
                       protein_present=0.85, isoform_match=0.8,
                       disease_features_match=0.85, dependency_signal=0.6,
                       genetic_tractable=0.5, provenance_ok=1.0, prior_use=0.3),
        ModelCandidate("KPC GEMM (LSL-KrasG12D;Trp53;Pdx1-Cre)", "in_vivo",
                       source="JAX / CRO", mrna_expressed=0.9,
                       protein_present=0.9, isoform_match=0.85,
                       disease_features_match=0.95, dependency_signal=0.7,
                       genetic_tractable=0.6, provenance_ok=1.0, prior_use=0.6),
        # scientifically-valid rejection: high mRNA, but only the truncated
        # isoform lacking the catalytic DHHC domain -> enzyme non-functional.
        ModelCandidate("DHHC-truncated PDAC line (isoform w/o DHHC domain)", "2d_line",
                       source="(illustrative)", mrna_expressed=0.85,
                       protein_present=0.6, isoform_match=0.05,
                       disease_features_match=0.7, dependency_signal=0.2,
                       genetic_tractable=0.9, provenance_ok=1.0, prior_use=0.1),
    ]

# Per-model capability overrides for the mechanism-context matcher. Most models
# inherit their tier's capabilities; the co-culture explicitly carries an immune
# compartment (that's the point of building it), and the truncated line is a plain
# 2D line. In the real tool these come from the model's documented composition.
MODEL_CAP_OVERRIDES = {
    "PDAC organoid + autologous T-cell co-culture": {"add_native": ["immune_compartment"]},
}

def apply_pathway(cands, relations, moa_context, question_type):
    """Run the two science checks per model and write them onto each candidate:
      (1) pathway coherence — is the enzyme present + its pathway intact
      (2) mechanism context — can the MoA's readout even be OBSERVED in this model,
          and what must be added to the culture to make it observable.
    Gate rests on the enzyme itself plus any REQUIRED, non-retrofittable context."""
    pw_by_model, moa_by_model = {}, {}
    for c in cands:
        expr = MODEL_COEXPRESSION.get(c.name, {})
        pw = pathway.pathway_coherence(expr, relations,
                                  target_present=c.protein_present,
                                  catalytic_domain_ok=MODEL_CATALYTIC_OK.get(c.name, True))
        c.pathway_coherence = pw["pathway_coherence"] if pw["pathway_coherence"] is not None else 0.5
        c.passed_science_gate = (pw["passed_science_gate"] is not False)
        mo = mechanism.match_model_context(c.tier, moa_context, question_type,
                                     capability_overrides=MODEL_CAP_OVERRIDES.get(c.name))
        c.context_fit = mo["context_fit"]
        c.context_required_unmet = mo["context_required_unmet"]
        pw_by_model[c.name] = pw
        moa_by_model[c.name] = mo
    return cands, pw_by_model, moa_by_model

if __name__ == "__main__":
    facts = build_facts()
    iso, pro = facts["isoforms"], facts["proteomics"]
    relations = facts["relations"]
    print("=== LIVE FACTS (ZDHHC20 / PDAC) ===")
    print(f"OT direct assoc: {facts['ot_direct_assoc']}  | SM-tractable: {facts['sm_tractable']}")
    print(f"Sourceable PDAC models: {facts['n_sourceable_models']} ({facts['n_problematic']} flagged)")
    print(f"Isoforms: {iso['n_protein_coding']} protein-coding, span {iso['aa_span']}, "
          f"risk={iso['isoform_specificity_risk']}")
    print(f"Proteomics: RNA '{pro['rna_tissue_distribution']}' vs PROTEIN "
          f"'{pro['protein_tissue_distribution']}' -> discordant={pro['mrna_protein_discordant']}")
    print(f"Modality routing: {pro['modalities']['note']}")
    pe = facts["protein_evidence"]
    print(f"PRIDE MS detectability: n={facts['pride']['n_projects']} projects "
          f"(tier={facts['pride']['tier']}) for UniProt {facts['pride']['uniprot']}")
    print(f"Tiered protein evidence: present={pe['protein_present']} "
          f"confidence={pe['confidence']} tiers={pe.get('tiers_used')} "
          f"| MS-absence guard applied={pe['ms_absence_guard_applied']}")
    print(f"STRING top partners: {[p['partner'] for p in facts['string_partners'][:5]]}")
    print("Literature-derived relations (partner -> relation_type, gates?):")
    for g, r in relations.items():
        print(f"    {g:7s} {r['relation_type']:26s} gates_selection={r['gates_model_selection']} "
              f"pmids={r.get('evidence_pmids')}")

    # MoA -> culture-context requirements (cached literature-derived; produced live
    # by mechanism.build_moa_context in the repl tool). This drives whether the mechanism's
    # readout is even OBSERVABLE in a given model, and what to add to the culture.
    moa_context = mechanism.ZDHHC20_MOA_CONTEXT
    print("\nMoA culture-context requirements (mechanism -> model):")
    for r in moa_context["requirements"]:
        pm = ",".join(r.get("evidence_pmids") or []) or ("hypothesis" if r.get("needs_verification") else "-")
        print(f"    {r['condition']:20s} {r['necessity']:10s} retrofit={str(r['retrofittable']):5s} "
              f"q={r['applies_to_questions']} [PMID {pm}]")

    target_context = {"symbol": "ZDHHC20"}
    # Two questions, to show the SAME target routing to DIFFERENT models:
    #   target_validation  — EGFR-ligand readout is retrofittable into a 2D line
    #   immune_mechanism   — needs an immune compartment a 2D line can't provide -> context gate
    for qtype in ["target_validation", "immune_mechanism"]:
        cands, pw_by_model, moa_by_model = apply_pathway(candidates(), relations,
                                                         moa_context, qtype)
        res = rank(cands, qtype)
        print(f"\n{'='*74}\nQUESTION: {qtype}\n{'='*74}")
        print(f"VERDICT: {res['verdict']}  (in-vivo: {res['in_vivo_recommended']})")
        print("\nRanked (science-gated):")
        for i, c in enumerate(res["ranked"], 1):
            print(f"  {i}. {c['name']:<46} total={c['scores']['total']:.2f} "
                  f"[sci={c['scores']['science_score']:.2f} tech={c['scores']['tech_score']:.2f} "
                  f"ctx={c['scores'].get('context_fit',0):.2f} gate={c['scores']['gate']}]")
        # full cards: the winner + a 2D line to show the mechanism-context behaviour
        # (retrofittable ligand for target_validation; hard context gate for immune).
        print("\n" + "-"*74 + "\nDECISION CARDS\n" + "-"*74)
        show = ([res["ranked"][0]]
                + [c for c in res["ranked"] if "PANC-1" in c["name"]])
        if qtype == "target_validation":
            show += [c for c in res["ranked"] if "truncated" in c["name"]]
        seen = set()
        for cd in show:
            if cd["name"] in seen:
                continue
            seen.add(cd["name"])
            print("\n" + render_card_text(
                make_card(cd, qtype, target_context, iso, pro,
                          pw_by_model.get(cd["name"]), moa_by_model.get(cd["name"]))))
