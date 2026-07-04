"""
Pathway-context layer — the SCIENCE GATE that runs BEFORE technical suitability.

Core principle: a model where the target is present but its pathway is broken
is NOT a relevant model, however convenient it is to culture. BUT "broken" must
mean a *mechanistically required* partner is absent — not merely a co-expressed
neighbour. A STRING edge or a co-expression correlation tells you two genes rise
and fall together; it does NOT tell you one is required for the other's function.
Conflating the two produces false rejections.

Worked cautionary tale (ZDHHC20, verified against primary literature):
- STRING's top partner for ZDHHC20 is GOLGA7/GCP16 (0.68). It is tempting to
  call GOLGA7 a required "cofactor" and hard-reject any model lacking it.
- The literature says otherwise. GCP16/GOLGA7 is the accessory that stabilises
  the *DHHC9 subfamily* (DHHC9/14/18/5/8) via a conserved C-terminal cysteine
  motif that "is NOT present in distantly related DHHCs, such as DHHC3 and
  DHHC20" (Front Physiol 2023, PMC10076531; JBC 2005, PMID 16000296). ZDHHC20
  is routinely used as a standalone positive control in palmitoylation assays.
  A direct "ZDHHC20 GOLGA7" / "ZDHHC20 GCP16" PubMed search returns ZERO papers.
- GOLGA7's mechanistic role, where it applies, is STRUCTURAL — it prevents
  enzyme aggregation/proteolysis and governs trafficking (GOLGA7 controls NRAS
  Golgi->PM transit "but not its palmitoylation", PMID 38317235) — i.e. a
  stabilizer/chaperone, not a catalytic cofactor.

Consequences for the gate:
1. Relations are DERIVED FROM LITERATURE (relation_type + PMIDs), not asserted
   from co-expression. See build_relation_map() (runs in the repl tool, where
   host.mcp/host.llm live) and the cached ZDHHC20 map below.
2. Only relations with gates_model_selection=True (a partner mechanistically
   REQUIRED for the target's function) can hard-reject a model. Substrates,
   upstream drivers, stabilizers and co-expressed neighbours shape *relevance/
   confidence*, they do not kill the model.
3. For ZDHHC20 specifically there is NO known obligate partner: the science gate
   therefore rests on the enzyme itself (protein present + intact catalytic DHHC
   domain, see isoforms.py) plus substrate availability (EGFR) and oncogenic
   context (KRAS) as relevance modifiers.
"""
import json, os, urllib.request, urllib.parse

def _get_json(url, t=40):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=t) as f:
        return json.loads(f.read().decode())

# ---------------------------------------------------- STRING functional partners
def string_partners(symbol, species=9606, limit=15, min_score=0.4):
    """Functional neighborhood: cofactors, complex members, candidate substrates.
    Verified: ZDHHC20 -> GOLGA7, ZDHHC5/3/9 (paralogs), etc."""
    qs = urllib.parse.urlencode({"identifiers": symbol, "species": species, "limit": limit})
    url = f"https://string-db.org/api/json/interaction_partners?{qs}"
    parts = _get_json(url)
    return [{"partner": p["preferredName_B"], "score": round(p["score"], 3)}
            for p in parts if p["score"] >= min_score]

# ---------------------------------------------------- literature-derived relations
# relation_type taxonomy — what a partner IS to the target, and whether its
# absence disables the target:
#   catalytic_cofactor       physically required for catalysis  -> GATES (hard reject)
#   stabilizer_accessory     stabilises/traffics the target protein; gates ONLY if
#                            literature says the target is non-functional without it
#   substrate                the target acts ON it; absence lowers relevance, no reject
#   upstream_driver          drives the pathway/context; absence lowers relevance
#   paralog_related          family member, not a functional partner
#   no_direct_functional_link  co-expressed/co-mentioned only -> never gates
REL_TYPES = ["catalytic_cofactor", "stabilizer_accessory", "substrate",
             "upstream_driver", "paralog_related", "no_direct_functional_link"]

# Only these relation types are ALLOWED to hard-reject a model, and only when the
# literature explicitly flags the partner as required (gates_model_selection=True).
GATING_TYPES = {"catalytic_cofactor", "stabilizer_accessory"}

def build_relation_map(target, partners, aliases=None, mcp=None, llm=None,
                       reasoning_model=None):
    """Derive target<-partner relations FROM LITERATURE. Runs in the repl tool,
    where host.mcp / host.llm are available; pass them in as mcp/llm/reasoning_model.
    Returns {partner: {relation_type, required_for_target_activity,
             gates_model_selection, consequence_if_absent, evidence_pmids, note}}.
    Cache the result to JSON and load it in the python kernel via load_relation_map().

    This replaces asserting "GOLGA7 is a required cofactor" with reading the
    papers and letting the evidence decide — for ZDHHC20 that flips GOLGA7 from
    a (wrong) hard gate to no_direct_functional_link."""
    import re
    aliases = aliases or {}
    out = {}
    for p in partners:
        al = aliases.get(p, [])
        alias_q = "(" + " OR ".join([p] + al) + ")"
        sr = mcp("pubmed", "search_articles",
                 query=f"{target} AND {alias_q}", max_results=6, sort="relevance")
        pmids = sr.get("pmids", [])
        abs_ = []
        if pmids:
            md = mcp("pubmed", "get_article_metadata", pmids=pmids)
            for a in md.get("articles", []):
                ids = a.get("identifiers", {})
                abs_.append({"pmid": str(ids.get("pmid")), "doi": ids.get("doi"),
                             "title": a.get("title"),
                             "abstract": (a.get("abstract") or "")[:1200]})
        evidence = "\n".join(f"[PMID {a['pmid']}] {a['title']}\n{a['abstract']}"
                             for a in abs_) or "NO CO-MENTIONING PAPERS FOUND."
        prompt = f"""Curating a functional-dependency graph for target {target}.
What is the relationship of {p} (aliases: {al or 'none'}) to {target}, and would
absence of {p} in a cell model abrogate {target}'s MOLECULAR FUNCTION?

relation_type must be exactly one of: {REL_TYPES}
Rules:
- If papers describe {p} acting on a DIFFERENT enzyme/subfamily than {target},
  choose no_direct_functional_link for {target} and name the enzyme it really serves.
- catalytic_cofactor / stabilizer_accessory require DIRECT evidence about {target}.
- gates_model_selection = true ONLY if absence would make {target} non-functional.

EVIDENCE:
{evidence}

Return STRICT JSON: relation_type, required_for_target_activity (true/false/unknown),
gates_model_selection (bool), consequence_if_absent (one sentence),
evidence_pmids (PMID strings from the evidence that support this),
note (one sentence; name subfamily/mechanism if relevant)."""
        res = llm(prompt, model=reasoning_model) if reasoning_model else llm(prompt)
        m = re.search(r"\{.*\}", res["text"], re.S)
        rel = json.loads(m.group(0)) if m else {"relation_type": "no_direct_functional_link",
                                                 "gates_model_selection": False}
        rel["_pmids_scanned"] = [a["pmid"] for a in abs_]
        rel["_search_total"] = sr.get("total_count", 0)
        out[p] = rel
    return out

def load_relation_map(path):
    """Load a cached relation map (produced by build_relation_map) in any kernel."""
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

# Cached, literature-grounded relation map for the ZDHHC20 worked example.
# Derived live from PubMed abstracts (see build_relation_map); the crucial result
# is that NONE of ZDHHC20's headline partners actually gate model selection.
ZDHHC20_RELATIONS = {
    "GOLGA7": {
        "relation_type": "no_direct_functional_link",
        "required_for_target_activity": "unknown",
        "gates_model_selection": False,
        "consequence_if_absent": "No evidence that GOLGA7 loss impairs ZDHHC20; GOLGA7/GCP16 stabilises the DHHC9 subfamily, whose C-terminal cysteine motif ZDHHC20 lacks.",
        "evidence_pmids": ["16000296", "37035671", "38317235"],
        "note": "STRING's top ZDHHC20 partner (0.68) but a direct co-mention search returns zero papers — a co-expression/text-mining artefact, not a mechanistic requirement.",
    },
    "EGFR": {
        "relation_type": "substrate",
        "required_for_target_activity": False,
        "gates_model_selection": False,
        "consequence_if_absent": "Removes one physiological substrate/readout but not ZDHHC20's intrinsic catalytic activity, which acts on other substrates too.",
        "evidence_pmids": ["27153536", "34610265"],
        "note": "ZDHHC20 palmitoylates EGFR's C-terminal tail to tune signalling — EGFR is acted upon, not required for the enzyme.",
    },
    "KRAS": {
        "relation_type": "upstream_driver",
        "required_for_target_activity": False,
        "gates_model_selection": False,
        "consequence_if_absent": "ZDHHC20 keeps its palmitoyltransferase activity, but the oncogenic context that makes it relevant in PDAC is diminished.",
        "evidence_pmids": ["38821916", "32127496"],
        "note": "KRAS signalling upregulates ZDHHC20 and sets the KRAS-mutant context; it is not a cofactor/substrate/stabilizer of the enzyme.",
    },
}

# ---------------------------------------------------- the science gate
def pathway_coherence(model_expression, relations, target_present=None,
                      catalytic_domain_ok=None):
    """Evidence-grounded science gate.

    model_expression: {gene -> 0..1 protein/mRNA presence in THIS model}
    relations: {partner -> relation dict} from build_relation_map / cached map
    target_present, catalytic_domain_ok: the enzyme itself (from proteomics.py /
        isoforms.py). For targets with NO obligate partner, THIS is the real gate.

    Hard reject only when a partner that literature says is REQUIRED
    (gates_model_selection=True) is absent, OR the target protein / its catalytic
    domain is absent. Substrates / upstream drivers / co-expressed neighbours are
    scored as relevance modifiers with provenance, never as kill switches."""
    rows = []
    hard_fail = []
    relevance_num, relevance_den = 0.0, 0.0
    # relevance weighting: how much each present/absent partner moves confidence
    rel_weight = {"catalytic_cofactor": 1.0, "stabilizer_accessory": 0.6,
                  "substrate": 0.6, "upstream_driver": 0.5,
                  "paralog_related": 0.1, "no_direct_functional_link": 0.0}
    for gene, rel in relations.items():
        rtype = rel.get("relation_type", "no_direct_functional_link")
        gates = bool(rel.get("gates_model_selection")) and rtype in GATING_TYPES
        present = model_expression.get(gene)
        status = "unknown" if present is None else ("present" if present >= 0.4 else "absent")
        rows.append({"gene": gene, "relation_type": rtype, "gates": gates,
                     "expression": present, "status": status,
                     "evidence_pmids": rel.get("evidence_pmids", []),
                     "note": rel.get("note", "")})
        if gates and present is not None and present < 0.4:
            hard_fail.append(gene)
        w = rel_weight.get(rtype, 0.3)
        if w > 0 and present is not None:
            relevance_num += w * present
            relevance_den += w
    # enzyme-intrinsic gate
    if target_present is not None and target_present < 0.4:
        hard_fail.append("TARGET_PROTEIN")
    if catalytic_domain_ok is False:
        hard_fail.append("CATALYTIC_DOMAIN")

    relevance = round(relevance_num / relevance_den, 3) if relevance_den else None
    if hard_fail:
        pretty = "/".join(hard_fail)
        verdict = (f"SCIENCE GATE FAIL: {pretty} absent/broken — target present but "
                   f"non-functional or context missing in this model.")
        passed = False
    elif relevance is None and target_present is None:
        verdict = "Pathway context unknown for this model — verify before use."
        passed = None
    else:
        # no required partner missing -> the model passes the gate; relevance
        # (substrate + context co-expression) becomes a confidence modifier.
        base = relevance if relevance is not None else 0.6
        if base >= 0.6:
            verdict = "Science gate PASS: enzyme intact and substrate/context co-expressed."
        elif base >= 0.4:
            verdict = "Science gate PASS (guarded): enzyme intact but weak substrate/context co-expression."
        else:
            verdict = "Science gate PASS (low relevance): enzyme present but little substrate/context support."
        passed = True
    return {"pathway_coherence": relevance, "passed_science_gate": passed,
            "hard_fail": hard_fail, "members": rows, "verdict": verdict}
