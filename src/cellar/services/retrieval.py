"""
Retrieval layer — thin clients over public + licensed sources.
Person A owns this file. Every function returns plain dicts (JSON-serializable)
so the scoring/judge layer stays decoupled from HTTP.

Verified live against the real APIs for ZDHHC20 / PDAC (see docstrings).
"""
import json
import urllib.parse
import urllib.request

def _post(url, payload, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.loads(f.read().decode())

def _get(url, headers=None, timeout=60):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.loads(f.read().decode())

# ---------------------------------------------------------------- Open Targets
OT = "https://api.platform.opentargets.org/api/v4/graphql"

def ot_resolve_target(symbol):
    """gene symbol -> ensembl id. Verified: ZDHHC20 -> ENSG00000180776."""
    q = 'query($s:String!){search(queryString:$s,entityNames:["target"]){hits{id name}}}'
    hits = _post(OT, {"query": q, "variables": {"s": symbol}})["data"]["search"]["hits"]
    return hits[0]["id"] if hits else None

def ot_resolve_disease(name):
    """disease name -> MONDO id. Verified: PDAC -> MONDO_0005184."""
    q = 'query($s:String!){search(queryString:$s,entityNames:["disease"]){hits{id name}}}'
    hits = _post(OT, {"query": q, "variables": {"s": name}})["data"]["search"]["hits"]
    return hits[0] if hits else None

def ot_target_profile(ensembl_id):
    """Tractability + top associated diseases. Drives the 'is this druggable +
    does the DB even know about this disease link' scoring inputs."""
    q = """query($id:String!){target(ensemblId:$id){
        approvedSymbol
        tractability{modality label value}
        associatedDiseases(page:{index:0,size:10}){rows{score disease{id name}}}
    }}"""
    t = _post(OT, {"query": q, "variables": {"id": ensembl_id}})["data"]["target"]
    return {
        "symbol": t["approvedSymbol"],
        "tractability": [x for x in t["tractability"] if x["value"]],
        "top_diseases": [(r["disease"]["name"], round(r["score"], 3))
                         for r in t["associatedDiseases"]["rows"]],
    }

def ot_assoc_score(ensembl_id, mondo_id):
    """Direct target<->disease association score. For ZDHHC20/PDAC this is ~0 —
    the deliberate teaching case: low DB score != weak target."""
    q = """query($d:String!){disease(efoId:$d){
        associatedTargets(page:{index:0,size:500}){rows{score target{id}}}}}"""
    rows = _post(OT, {"query": q, "variables": {"d": mondo_id}}
                 )["data"]["disease"]["associatedTargets"]["rows"]
    for r in rows:
        if r["target"]["id"] == ensembl_id:
            return round(r["score"], 4)
    return 0.0

# ---------------------------------------------------------------- Cellosaurus
CELLO = "https://api.cellosaurus.org/search/cell-line"

def cello_models(disease_term, rows=1000):
    """All sourceable models for a disease. Verified: PDAC -> 333 models,
    7 flagged problematic. Returns list of {id, ac, category, problematic}."""
    qs = urllib.parse.urlencode({"q": f'di:"{disease_term}"', "format": "json",
                                 "rows": str(rows), "fields": "id,ac,ca,cc,di"})
    d = _get(f"{CELLO}?{qs}", headers={"Accept": "application/json"})
    out = []
    for c in d.get("Cellosaurus", {}).get("cell-line-list", []):
        blob = json.dumps(c).lower()
        out.append({
            "id": c.get("accession", c.get("id")),
            "name": c.get("name") or (c.get("name-list") or [{}])[0].get("value"),
            "category": c.get("category"),
            "problematic": ("problematic" in blob or "misidentif" in blob),
        })
    return out

# ---------------------------------------------------------------- DepMap (Sanger)
# The Sanger DepMap's curated model + genomics hub is Cell Model Passports, which
# has a public JSON:API. The old depmap_stub placeholder is replaced by that live
# client: see services.cell_model_passports (model_facts, model_gene_mutations,
# per-model expression/CRISPR datasets).
