"""
Evidence layer — Elicit + Amass query templates.
These are the wedge for cases like ZDHHC20/PDAC where structured DBs show ~0
association but the primary literature is rich. Fill in your API keys/MCP.

Both return list-of-dicts with a `citations` field so the judge cites sources.
"""

# --------------------------------------------------------------- ELICIT
# Elicit = deep structured extraction: one row per paper, your columns.
# Use it for the "prior use of this model" and per-model-caveat dimensions.
ELICIT_PRIOR_USE = (
    "For studies of {target} in {disease}, extract: the in vitro or in vivo "
    "model used (cell line / organoid / co-culture / mouse), the specific model "
    "name, the assay/readout, and the main functional finding."
)
ELICIT_MODEL_CAVEATS = (
    "For the model system {model_name} used in {disease} research, extract: "
    "reported limitations, whether {target} is expressed/functional, culture "
    "format, and doubling time or throughput notes."
)

def elicit_prior_use(target, disease, client=None):
    """Return [{paper, model_type, model_name, assay, finding, doi}]. Wire to
    Elicit's list-extraction endpoint / MCP. Stubbed for offline demo."""
    if client is None:
        return [{"paper": "STUB — wire Elicit here", "model_type": "organoid",
                 "model_name": "patient-derived PDAC organoid", "assay": "viability",
                 "finding": f"{target} palmitoylation supports KRAS signaling", "doi": ""}]
    return client.extract(ELICIT_PRIOR_USE.format(target=target, disease=disease))

# --------------------------------------------------------------- AMASS
# Amass = broad multi-core retrieval. base: https://api.amass.tech/api/v1
# Cores: BioMedCore, ScholarCore, PatentCore, RegulatoryCore, TrialCore, WebCore.
# No pagination: use limit<=300 with specific queries.
AMASS_BASE = "https://api.amass.tech/api/v1"

def amass_search(core, query, limit=50, api_key=None):
    """POST /v1/cores/{core}/search — returns cited hits. Fill auth header."""
    import json
    import urllib.request
    url = f"{AMASS_BASE}/cores/{core}/search"
    body = json.dumps({"query": query, "limit": min(limit, 300)}).encode()
    hdr = {"Content-Type": "application/json"}
    if api_key: hdr["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=body, headers=hdr)
    with urllib.request.urlopen(req, timeout=60) as f:
        return json.loads(f.read().decode())

# Which Amass core answers which decision dimension:
AMASS_PLAYBOOK = {
    # track record: did this model type support a clinical program for this disease
    "track_record": ("TrialCore", "{disease} {target} preclinical model"),
    # regulatory NAM acceptance for the assay class
    "nam_acceptance": ("RegulatoryCore", "{model_type} qualification new approach methodology"),
    # supplier / CRO sourcing — partly automates the hand-curated table
    "sourcing":      ("WebCore", "{model_type} {disease} commercial supplier OR CRO"),
    "ip_landscape":  ("PatentCore", "{model_type} {disease} {target}"),
}

def amass_dimension(dim, api_key=None, **fmt):
    core, tmpl = AMASS_PLAYBOOK[dim]
    return amass_search(core, tmpl.format(**fmt), api_key=api_key)
