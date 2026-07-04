"""
Proteomics layer — because mRNA is a poor proxy for protein.
For ZDHHC20 (verified live in HPA): RNA "Detected in all" tissues but PROTEIN
"Detected in some" — the discordance is real and on-target.

Three jobs:
  1. Pull protein-level presence/abundance (not mRNA) from a TIERED hierarchy of
     databases, not from HPA alone (HPA is human-TISSUE antibody evidence; it
     does not tell you whether the cell line/organoid you would culture makes the
     protein). See synthesize_protein_evidence() for the hierarchy.
  2. Route to the RIGHT proteomics modality for the target's biology, because
     Olink/SomaScan (affinity plasma proteomics) only see secreted/plasma
     proteins — an intracellular membrane enzyme like ZDHHC20 will be ABSENT
     from them by design, which would be misread as "not expressed".
  3. Apply the MS-ABSENCE GUARD: low or zero mass-spec detectability is WEAK
     evidence, never proof of absence. Multipass membrane and low-abundance
     proteins are systematically under-sampled by shotgun MS. Verified live:
     ZDHHC20 (UniProt Q5W0Z9) is identified in ZERO PRIDE MS projects, yet is a
     real, antibody- and function-validated protein. A naive "not in PRIDE ->
     reject" filter would wrongly kill exactly the tractable membrane enzymes
     this tool exists to rescue.

Tiered protein-evidence hierarchy (highest value for MODEL SELECTION first):
  1. model_specific   DepMap/CCLE proteomics — does THIS cell line express it
  2. tumor_quant      CPTAC/PDC — tumor-vs-normal quant abundance + phosphosites
  3. localization_ab  HPA — subcellular compartment + antibody tissue/tumor IHC
  4. ms_detectability PRIDE/PaxDb — is it MS-detectable at all, at what tier
  5. modality_guard   Olink/SomaScan router — don't commission a plasma panel
                      for an intracellular target
"""
import json
import os
import urllib.request

def _get(url, t=60):
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=t) as f:
        return json.loads(f.read().decode())

# ------------------------------------------------------- modality router
# NB: "plasma membrane" is an INTRACELLULAR-anchored membrane location, NOT
# blood plasma — it must never trigger the affinity-plasma modality. Affinity
# panels (Olink/SomaScan) only see soluble secreted/extracellular proteins.
SECRETED_HINTS = ("secreted", "extracellular", "blood plasma", "plasma protein")
MEMBRANE_HINTS = ("plasma membrane", "membrane", "vesicle", "golgi", "er",
                  "endoplasmic", "mitochond", "nucle", "cytosol", "cytoplasm")

def valid_proteomics_modalities(subcellular_locations, protein_class=None):
    """Given HPA subcellular locations (+ optional protein class), return which
    proteomics evidence sources are biologically valid for this target."""
    loc = " ".join(subcellular_locations).lower()
    cls = " ".join(protein_class or []).lower()
    membrane_or_intracellular = any(h in loc for h in MEMBRANE_HINTS) or "membrane" in cls
    secreted = (any(h in loc for h in SECRETED_HINTS) or "secreted" in cls) \
               and not membrane_or_intracellular
    return {
        "MS_tissue_tumor": True,          # CPTAC/HPA MS — always valid (whole-cell lysate)
        "olink_somascan_plasma": secreted, # affinity plasma — ONLY if truly secreted
        "note": ("target is secreted/extracellular -> Olink/SomaScan plasma panels apply"
                 if secreted else
                 "intracellular/membrane target -> Olink/SomaScan will NOT detect it; "
                 "use MS-based (CPTAC/HPA) protein evidence instead"),
    }

# ------------------------------------------------------- HPA protein evidence
def hpa_protein_evidence(ensembl_id, disease_hint="Pancreatic"):
    """MS-based protein presence + mRNA-vs-protein discordance + cancer signal.
    Verified live for ZDHHC20/ENSG00000180776."""
    d = _get(f"https://www.proteinatlas.org/{ensembl_id}.json")
    subloc = d.get("Subcellular location") or d.get("Subcellular main location") or []
    rna_dist = d.get("RNA tissue distribution")
    prot_dist = d.get("Protein tissue distribution")
    # discordance flag: mRNA broad but protein narrow
    discordant = (rna_dist == "Detected in all") and (prot_dist not in
                 (None, "Detected in all"))
    # disease-specific protein prognostic signal
    prog = {k: v for k, v in d.items()
            if k.startswith("Cancer prognostics") and disease_hint.lower() in k.lower()}
    return {
        "subcellular": subloc,
        "protein_class": d.get("Protein class"),
        "rna_tissue_distribution": rna_dist,
        "protein_tissue_distribution": prot_dist,
        "mrna_protein_discordant": discordant,
        "protein_cell_type_intensity": d.get("Protein cell type specific Intensity"),
        "disease_protein_prognostic": prog,
        "modalities": valid_proteomics_modalities(subloc, d.get("Protein class")),
    }

# ------------------------------------------------------- PRIDE MS detectability
# PRIDE / ProteomeXchange is the master mass-spec repository. The protein->projects
# direction (pride_find_projects_for_protein) answers "in how many independent MS
# studies has this protein ever been identified" — a DETECTABILITY PRIOR, not a
# presence/absence call. Runs in the repl tool (host.mcp); pass mcp= and cache
# the result for offline demo use (see ZDHHC20_PRIDE below).
def pride_ms_detectability(uniprot_accession, mcp=None):
    """{n_projects, tier, is_detectable, projects[:20]}. LOW/ZERO tiers are WEAK
    evidence — never proof of absence (see MS-absence guard)."""
    r = mcp("omics-archives", "pride_find_projects_for_protein",
            protein_accession=uniprot_accession)
    recs = r.get("records", []) or []
    n = r.get("n_records", len(recs))
    return {"uniprot": uniprot_accession, "n_projects": n,
            "tier": ms_detectability_tier(n), "is_detectable": n > 0,
            "projects": [x.get("accession") or x.get("project_accession")
                         for x in recs[:20]]}

def ms_detectability_tier(n_projects):
    if n_projects == 0:   return "undetected"     # absent from the MS archive
    if n_projects < 5:    return "low"            # sporadic identifications
    if n_projects < 25:   return "moderate"
    return "high"                                  # robustly MS-detectable

def load_pride_cache(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

# Cached live probe (2024): ZDHHC20 UniProt Q5W0Z9 -> 0 PRIDE MS projects.
# This is the worked proof of the MS-absence guard: undetected in MS, yet real.
ZDHHC20_PRIDE = {"uniprot": "Q5W0Z9", "n_projects": 0, "tier": "undetected",
                 "is_detectable": False, "projects": []}

# ------------------------------------------------------- CPTAC / PDC (tumor quant)
# CPTAC PDAC mass-spec (gold standard for THIS tumor) lives at the PDC GraphQL
# endpoint (proteomic.datacommons.cancer.gov) — needs allowlist approval; cache
# the ZDHHC20 tumor-vs-normal protein quant CSV once for the demo. When wired,
# return {detected, tumor_vs_normal_log2fc, phosphosites, n_tumors}.
def cptac_tumor_quant(gene, tumor="PDAC", detected=None, log2fc=None,
                      phosphosites=None, n_tumors=None):
    return {"gene": gene, "tumor": tumor, "detected": detected,
            "tumor_vs_normal_log2fc": log2fc, "phosphosites": phosphosites,
            "n_tumors": n_tumors,
            "wired": detected is not None,
            "note": ("cached/live PDC quant" if detected is not None
                     else "wire PDC GraphQL or cache CPTAC PDAC protein quant CSV")}

# ------------------------------------------------------- DepMap / CCLE (model-specific)
# The highest-value tier for MODEL SELECTION: Gygi-lab TMT proteomics across
# ~375 cancer cell lines answers "does PANC-1 / MIA PaCa-2 specifically make this
# protein". Not the same as DepMap dependency (that is retrieval.depmap_stub).
# When wired, return {line -> {detected, protein_intensity_zscore}}.
def depmap_proteomics(gene, line_intensities=None):
    """line_intensities: {cell_line -> 0..1 relative protein intensity} if cached
    from the DepMap proteomics table; else a documented wiring point."""
    return {"gene": gene, "lines": line_intensities or {},
            "wired": bool(line_intensities),
            "note": ("cached DepMap/CCLE proteomics intensities" if line_intensities
                     else "wire DepMap 'proteomics' (Gygi TMT) table by cell line")}

def olink_somascan_stub(gene, subcellular):
    """Only meaningful if target is secreted/plasma. Guard against misuse."""
    v = valid_proteomics_modalities(subcellular)
    if not v["olink_somascan_plasma"]:
        return {"applicable": False, "reason": v["note"]}
    return {"applicable": True, "note": "query Olink Explore / SomaScan panel for " + gene}

# ------------------------------------------------------- tiered synthesis
# Weights = how much each tier is trusted as PROTEIN-PRESENCE evidence. Model- and
# tumor-level quant dominate; HPA localization is supportive; MS detectability is
# a prior, not a verdict.
TIER_WEIGHT = {"model_specific": 1.0, "tumor_quant": 0.9,
               "localization_ab": 0.6, "ms_detectability": 0.4}

def _is_ms_hard_class(protein_class, subcellular):
    """Classes that shotgun MS systematically under-detects -> the guard applies:
    multipass membrane, vesicle/Golgi/ER membrane, low-abundance enzymes."""
    cls = " ".join(protein_class or []).lower()
    loc = " ".join(subcellular or []).lower()
    return ("membrane" in cls or any(h in loc for h in
            ("membrane", "vesicle", "golgi", "endoplasmic", "er")))

def synthesize_protein_evidence(hpa=None, pride=None, cptac=None, depmap=None,
                                cell_line=None):
    """Combine the tiers into ONE protein-presence score + confidence + provenance.

    Returns {protein_present (0..1), confidence (0..1), provenance[list],
             caveats[list], ms_absence_guard_applied(bool), per_tier(dict)}.

    Design guarantees:
      * MODEL-SPECIFIC (DepMap for this line) and TUMOR-QUANT (CPTAC) evidence,
        when present, dominate — they are what HPA alone cannot provide.
      * MS undetectability lowers CONFIDENCE but does NOT drive protein_present to
        0 for an MS-hard class; instead it raises a caveat and the guard flag.
      * If a target is MS-detectable in general but a specific line lacks it, that
        is a real (model-level) negative and is allowed to lower the score.
    """
    per_tier, provenance, caveats = {}, [], []
    signals = []  # (tier, weight, signal 0..1)

    subloc = (hpa or {}).get("subcellular", [])
    pclass = (hpa or {}).get("protein_class", [])
    ms_hard = _is_ms_hard_class(pclass, subloc)

    # tier 1: model-specific (DepMap proteomics for THIS line)
    if depmap and depmap.get("wired") and cell_line in (depmap.get("lines") or {}):
        v = depmap["lines"][cell_line]
        per_tier["model_specific"] = v
        signals.append(("model_specific", TIER_WEIGHT["model_specific"], v))
        provenance.append(f"DepMap proteomics ({cell_line}) intensity={v:.2f}")
        if v < 0.4:
            caveats.append(f"{cell_line}: low protein intensity in DepMap proteomics "
                           "— model-level negative, not just an MS gap.")

    # tier 2: tumor quant (CPTAC/PDC)
    if cptac and cptac.get("wired"):
        det = 1.0 if cptac.get("detected") else 0.0
        per_tier["tumor_quant"] = cptac
        signals.append(("tumor_quant", TIER_WEIGHT["tumor_quant"], det))
        fc = cptac.get("tumor_vs_normal_log2fc")
        provenance.append(f"CPTAC {cptac.get('tumor')} detected={bool(cptac.get('detected'))}"
                          + (f", log2FC={fc}" if fc is not None else ""))

    # tier 3: HPA localization + antibody tissue evidence
    if hpa:
        prot_dist = hpa.get("protein_tissue_distribution")
        hpa_sig = (1.0 if prot_dist == "Detected in all" else
                   0.7 if prot_dist and "Detected in" in prot_dist else
                   0.3 if prot_dist else None)
        if hpa_sig is not None:
            per_tier["localization_ab"] = prot_dist
            signals.append(("localization_ab", TIER_WEIGHT["localization_ab"], hpa_sig))
            provenance.append(f"HPA protein '{prot_dist}', subcellular={subloc}")
        if hpa.get("mrna_protein_discordant"):
            caveats.append("mRNA broad but protein narrow (HPA) — confirm protein "
                           "by WB/IF in your lot; do not rely on RNA-seq.")

    # tier 4: MS detectability prior (PRIDE)
    if pride is not None:
        n = pride.get("n_projects", 0)
        ms_sig = {"undetected": 0.0, "low": 0.4, "moderate": 0.7, "high": 1.0}[pride["tier"]]
        per_tier["ms_detectability"] = pride
        provenance.append(f"PRIDE MS projects n={n} (tier={pride['tier']})")
        if pride["tier"] in ("undetected", "low"):
            if ms_hard:
                # GUARD: under-detection is expected for this class -> weak evidence
                caveats.append(
                    f"MS-absence guard: {pride['tier']} MS detectability (PRIDE n={n}) "
                    "is expected for a membrane/low-abundance target and is NOT "
                    "evidence of absence — weighted down, not used to reject.")
            else:
                # detectable class but absent -> a real negative, count it
                signals.append(("ms_detectability", TIER_WEIGHT["ms_detectability"], ms_sig))
                caveats.append(
                    f"MS detectability low (PRIDE n={n}) for a normally MS-visible "
                    "class — treat protein presence as unconfirmed.")
        else:
            signals.append(("ms_detectability", TIER_WEIGHT["ms_detectability"], ms_sig))

    if not signals:
        return {"protein_present": None, "confidence": 0.0, "provenance": provenance,
                "caveats": caveats or ["No protein-level evidence available."],
                "ms_absence_guard_applied": ms_hard and (pride or {}).get("tier")
                    in ("undetected", "low"),
                "per_tier": per_tier}

    num = sum(w * s for _, w, s in signals)
    den = sum(w for _, w, s in signals)
    protein_present = round(num / den, 3)

    # confidence: driven by whether DIRECT (model/tumor) evidence exists and how
    # many independent tiers agree; MS-hard targets with no direct evidence cap low.
    have_direct = any(t in ("model_specific", "tumor_quant") for t, _, _ in signals)
    base_conf = 0.4 + 0.15 * len(signals)
    if have_direct:
        base_conf += 0.2
    if ms_hard and not have_direct:
        base_conf = min(base_conf, 0.5)   # can't be confident on antibody+MS-gap alone
    confidence = round(min(base_conf, 0.95), 3)

    return {"protein_present": protein_present, "confidence": confidence,
            "provenance": provenance, "caveats": caveats,
            "ms_absence_guard_applied": bool(ms_hard and (pride or {}).get("tier")
                in ("undetected", "low")),
            "per_tier": per_tier,
            "tiers_used": [t for t, _, _ in signals]}
