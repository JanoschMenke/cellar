from typing import cast

from cellar.config import OPEN_TARGETS_URL as API_URL
from cellar.schemas.sources import OtDiseaseHit, OtTargetProfile, OtTractabilityRow
from cellar.utils import http

Json = dict[str, object]


def _gql(query: str, variables: dict[str, object]) -> Json:
    payload = cast(
        Json, http.post_json(API_URL, {"query": query, "variables": variables}, timeout=40)
    )
    if payload.get("errors"):
        errors = cast("list[Json]", payload["errors"])
        raise RuntimeError(f"Open Targets error: {errors[0].get('message')}")
    return cast(Json, payload["data"])


_SEARCH = (
    "query($s:String!,$e:[String!]){search(queryString:$s,entityNames:$e){hits{id name entity}}}"
)


def resolve_target(symbol: str) -> dict[str, str] | None:
    search = cast(Json, _gql(_SEARCH, {"s": symbol, "e": ["target"]})["search"])
    hits = cast("list[Json]", search["hits"])
    return {"ensembl_id": str(hits[0]["id"]), "name": str(hits[0]["name"])} if hits else None


def resolve_disease(name: str) -> dict[str, str] | None:
    search = cast(Json, _gql(_SEARCH, {"s": name, "e": ["disease"]})["search"])
    hits = cast("list[Json]", search["hits"])
    return {"disease_id": str(hits[0]["id"]), "name": str(hits[0]["name"])} if hits else None


def _enabled_tractability(rows: list[Json]) -> list[dict[str, str]]:
    return [{"modality": str(r["modality"]), "label": str(r["label"])} for r in rows if r["value"]]


_ASSOCIATION = """query($id:String!,$dis:[String!]){
  target(ensemblId:$id){
    approvedSymbol biotype
    tractability{modality label value}
    associatedDiseases(Bs:$dis){rows{score datatypeScores{id score} disease{id name}}}
  }
}"""


def target_disease_association(target_symbol: str, disease_name: str) -> dict[str, object]:
    target = resolve_target(target_symbol)
    if target is None:
        return {"found": False, "reason": f"target not found: {target_symbol}"}
    disease = resolve_disease(disease_name)
    if disease is None:
        return {"found": False, "reason": f"disease not found: {disease_name}"}
    data = cast(
        Json,
        _gql(_ASSOCIATION, {"id": target["ensembl_id"], "dis": [disease["disease_id"]]})["target"],
    )
    associated_diseases = cast(Json, data["associatedDiseases"])
    rows = cast("list[Json]", associated_diseases["rows"])
    row = rows[0] if rows else None
    tractability = _enabled_tractability(cast("list[Json]", data["tractability"]))
    sm_tractable = any(t["modality"] == "SM" for t in tractability)
    return {
        "found": True,
        "target": data["approvedSymbol"],
        "ensembl_id": target["ensembl_id"],
        "biotype": data.get("biotype"),
        "disease": disease["name"],
        "disease_id": disease["disease_id"],
        "overall_score": round(cast(float, row["score"]), 4) if row else 0.0,
        "datatype_scores": (
            {
                cast(Json, d)["id"]: round(cast(float, cast(Json, d)["score"]), 3)
                for d in cast("list[object]", row["datatypeScores"])
            }
            if row
            else {}
        ),
        "tractability": tractability,
        "small_molecule_tractable": sm_tractable,
        "underrated_flag": bool(row is None or cast(float, row["score"]) < 0.1) and sm_tractable,
    }


_TARGET_PROFILE = """query($id:String!,$size:Int!){
  target(ensemblId:$id){
    approvedSymbol biotype
    tractability{modality label value}
    associatedDiseases(page:{index:0,size:$size}){rows{score disease{id name}}}
  }
}"""


def target_profile(target_symbol: str, top_n: int = 10) -> dict[str, object]:
    target = resolve_target(target_symbol)
    if target is None:
        return {"found": False, "reason": f"target not found: {target_symbol}"}
    data = cast(Json, _gql(_TARGET_PROFILE, {"id": target["ensembl_id"], "size": top_n})["target"])
    tractability = _enabled_tractability(cast("list[Json]", data["tractability"]))
    associated_diseases = cast(Json, data["associatedDiseases"])
    return {
        "found": True,
        "target": data["approvedSymbol"],
        "ensembl_id": target["ensembl_id"],
        "biotype": data.get("biotype"),
        "tractability": tractability,
        "small_molecule_tractable": any(t["modality"] == "SM" for t in tractability),
        "top_diseases": [
            {
                "disease": cast(Json, r["disease"])["name"],
                "id": cast(Json, r["disease"])["id"],
                "score": round(cast(float, r["score"]), 4),
            }
            for r in cast("list[Json]", associated_diseases["rows"])
        ],
    }


_DISEASE_TARGETS = """query($id:String!,$size:Int!){
  disease(efoId:$id){
    name
    associatedTargets(page:{index:0,size:$size}){rows{score target{id approvedSymbol}}}
  }
}"""


def disease_top_targets(disease_name: str, top_n: int = 15) -> dict[str, object]:
    disease = resolve_disease(disease_name)
    if disease is None:
        return {"found": False, "reason": f"disease not found: {disease_name}"}
    data = cast(
        Json, _gql(_DISEASE_TARGETS, {"id": disease["disease_id"], "size": top_n})["disease"]
    )
    associated_targets = cast(Json, data["associatedTargets"])
    return {
        "found": True,
        "disease": data["name"],
        "disease_id": disease["disease_id"],
        "top_targets": [
            {
                "target": cast(Json, r["target"])["approvedSymbol"],
                "ensembl_id": cast(Json, r["target"])["id"],
                "score": round(cast(float, r["score"]), 4),
            }
            for r in cast("list[Json]", associated_targets["rows"])
        ],
    }


def ot_resolve_target(symbol: str) -> str | None:
    q = 'query($s:String!){search(queryString:$s,entityNames:["target"]){hits{id name}}}'
    response = cast(
        "dict[str, object]", http.post_json(API_URL, {"query": q, "variables": {"s": symbol}})
    )
    data = cast("dict[str, object]", response["data"])
    hits = cast("list[dict[str, object]]", cast("dict[str, object]", data["search"])["hits"])
    return str(hits[0]["id"]) if hits else None


def ot_resolve_disease(name: str) -> OtDiseaseHit | None:
    q = 'query($s:String!){search(queryString:$s,entityNames:["disease"]){hits{id name}}}'
    response = cast(
        "dict[str, object]", http.post_json(API_URL, {"query": q, "variables": {"s": name}})
    )
    data = cast("dict[str, object]", response["data"])
    hits = cast("list[dict[str, object]]", cast("dict[str, object]", data["search"])["hits"])
    if not hits:
        return None
    hit = hits[0]
    return OtDiseaseHit(id=str(hit["id"]), name=str(hit["name"]))


def ot_target_profile(ensembl_id: str) -> OtTargetProfile:
    q = """query($id:String!){target(ensemblId:$id){
        approvedSymbol
        tractability{modality label value}
        associatedDiseases(page:{index:0,size:10}){rows{score disease{id name}}}
    }}"""
    response = cast(
        "dict[str, object]", http.post_json(API_URL, {"query": q, "variables": {"id": ensembl_id}})
    )
    data = cast("dict[str, object]", response["data"])
    t = cast("dict[str, object]", data["target"])
    tractability = cast("list[dict[str, object]]", t["tractability"])
    associated = cast("dict[str, object]", t["associatedDiseases"])
    rows = cast("list[dict[str, object]]", associated["rows"])
    return OtTargetProfile(
        symbol=str(t["approvedSymbol"]),
        tractability=[
            OtTractabilityRow(
                modality=str(x["modality"]), label=str(x["label"]), value=bool(x["value"])
            )
            for x in tractability
            if x["value"]
        ],
        top_diseases=[
            (
                str(cast("dict[str, object]", r["disease"])["name"]),
                round(cast(float, r["score"]), 3),
            )
            for r in rows
        ],
    )


def ot_assoc_score(ensembl_id: str, mondo_id: str) -> float:
    q = """query($d:String!){disease(efoId:$d){
        associatedTargets(page:{index:0,size:500}){rows{score target{id}}}}}"""
    response = cast(
        "dict[str, object]", http.post_json(API_URL, {"query": q, "variables": {"d": mondo_id}})
    )
    data = cast("dict[str, object]", response["data"])
    disease = cast("dict[str, object]", data["disease"])
    associated = cast("dict[str, object]", disease["associatedTargets"])
    rows = cast("list[dict[str, object]]", associated["rows"])
    for r in rows:
        target = cast("dict[str, object]", r["target"])
        if target["id"] == ensembl_id:
            return round(cast(float, r["score"]), 4)
    return 0.0
