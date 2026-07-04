"""
Open Targets Platform (GraphQL) — target–disease association evidence and
druggability. This promotes the four ot_* helpers in retrieval.py to a proper
client.

Its role in the matchmaker is the *outside view* on the target: how strongly the
databases already link target->disease, broken down by evidence type, plus
tractability (is it even druggable). Crucially it also surfaces the pitch's
teaching case — a real, tractable target the databases UNDERRATE:

  verified live: ZDHHC20 vs pancreatic ductal adenocarcinoma -> overall
  association 0.0039 (only weak literature + rna_expression, no genetic/known-drug
  evidence), yet ZDHHC20 is small-molecule tractable ("Structure with Ligand").
  A naive association-score recommender discards it; the matchmaker rescues it via
  functional data + literature.

Endpoint: https://api.platform.opentargets.org/api/v4/graphql (public, no auth).
Note: the per-disease association filter argument is `Bs` (Open Targets' obfuscated
name for the disease-id list) — verified live; watch for schema churn.
"""
import json
import urllib.request

API_URL = "https://api.platform.opentargets.org/api/v4/graphql"


def _gql(query: str, variables: dict[str, object]) -> dict[str, object]:
    body = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request(
        API_URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        payload = json.loads(response.read().decode())
    if payload.get("errors"):
        raise RuntimeError(f"Open Targets error: {payload['errors'][0].get('message')}")
    return payload["data"]


_SEARCH = "query($s:String!,$e:[String!]){search(queryString:$s,entityNames:$e){hits{id name entity}}}"


def resolve_target(symbol: str) -> dict[str, str] | None:
    """Gene symbol -> Ensembl id. Verified: ZDHHC20 -> ENSG00000180776."""
    hits = _gql(_SEARCH, {"s": symbol, "e": ["target"]})["search"]["hits"]
    return {"ensembl_id": hits[0]["id"], "name": hits[0]["name"]} if hits else None


def resolve_disease(name: str) -> dict[str, str] | None:
    """Disease name -> EFO/MONDO id. Verified: PDAC -> MONDO_0005184."""
    hits = _gql(_SEARCH, {"s": name, "e": ["disease"]})["search"]["hits"]
    return {"disease_id": hits[0]["id"], "name": hits[0]["name"]} if hits else None


def _enabled_tractability(rows: list[dict[str, object]]) -> list[dict[str, str]]:
    return [{"modality": r["modality"], "label": r["label"]} for r in rows if r["value"]]


_ASSOCIATION = """query($id:String!,$dis:[String!]){
  target(ensemblId:$id){
    approvedSymbol biotype
    tractability{modality label value}
    associatedDiseases(Bs:$dis){rows{score datatypeScores{id score} disease{id name}}}
  }
}"""


def target_disease_association(target_symbol: str, disease_name: str) -> dict[str, object]:
    """Overall target-disease association + per-datatype breakdown + tractability.
    overall_score near 0 with SM tractability is the 'underrated target' signal."""
    target = resolve_target(target_symbol)
    if target is None:
        return {"found": False, "reason": f"target not found: {target_symbol}"}
    disease = resolve_disease(disease_name)
    if disease is None:
        return {"found": False, "reason": f"disease not found: {disease_name}"}
    data = _gql(_ASSOCIATION, {"id": target["ensembl_id"], "dis": [disease["disease_id"]]})["target"]
    rows = data["associatedDiseases"]["rows"]
    row = rows[0] if rows else None
    tractability = _enabled_tractability(data["tractability"])
    sm_tractable = any(t["modality"] == "SM" for t in tractability)
    return {
        "found": True,
        "target": data["approvedSymbol"],
        "ensembl_id": target["ensembl_id"],
        "biotype": data.get("biotype"),
        "disease": disease["name"],
        "disease_id": disease["disease_id"],
        "overall_score": round(row["score"], 4) if row else 0.0,
        "datatype_scores": (
            {d["id"]: round(d["score"], 3) for d in row["datatypeScores"]} if row else {}
        ),
        "tractability": tractability,
        "small_molecule_tractable": sm_tractable,
        "underrated_flag": bool(row is None or row["score"] < 0.1) and sm_tractable,
    }


_TARGET_PROFILE = """query($id:String!,$size:Int!){
  target(ensemblId:$id){
    approvedSymbol biotype
    tractability{modality label value}
    associatedDiseases(page:{index:0,size:$size}){rows{score disease{id name}}}
  }
}"""


def target_profile(target_symbol: str, top_n: int = 10) -> dict[str, object]:
    """Tractability + the target's top associated diseases (no disease filter)."""
    target = resolve_target(target_symbol)
    if target is None:
        return {"found": False, "reason": f"target not found: {target_symbol}"}
    data = _gql(_TARGET_PROFILE, {"id": target["ensembl_id"], "size": top_n})["target"]
    tractability = _enabled_tractability(data["tractability"])
    return {
        "found": True,
        "target": data["approvedSymbol"],
        "ensembl_id": target["ensembl_id"],
        "biotype": data.get("biotype"),
        "tractability": tractability,
        "small_molecule_tractable": any(t["modality"] == "SM" for t in tractability),
        "top_diseases": [
            {"disease": r["disease"]["name"], "id": r["disease"]["id"], "score": round(r["score"], 4)}
            for r in data["associatedDiseases"]["rows"]
        ],
    }


_DISEASE_TARGETS = """query($id:String!,$size:Int!){
  disease(efoId:$id){
    name
    associatedTargets(page:{index:0,size:$size}){rows{score target{id approvedSymbol}}}
  }
}"""


def disease_top_targets(disease_name: str, top_n: int = 15) -> dict[str, object]:
    """Top associated targets for a disease — the leaderboard the matchmaker
    deliberately looks beyond (KRAS tops PDAC; ZDHHC20 is nowhere near it)."""
    disease = resolve_disease(disease_name)
    if disease is None:
        return {"found": False, "reason": f"disease not found: {disease_name}"}
    data = _gql(_DISEASE_TARGETS, {"id": disease["disease_id"], "size": top_n})["disease"]
    return {
        "found": True,
        "disease": data["name"],
        "disease_id": disease["disease_id"],
        "top_targets": [
            {"target": r["target"]["approvedSymbol"], "ensembl_id": r["target"]["id"], "score": round(r["score"], 4)}
            for r in data["associatedTargets"]["rows"]
        ],
    }
