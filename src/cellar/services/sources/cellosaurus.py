import json
import urllib.parse
from typing import cast

from cellar.config import CELLOSAURUS_URL as API_BASE
from cellar.schemas.sources import CellModelHit, CommercialListing, Provenance
from cellar.utils import http

_COMPACT_FIELDS = "id,ac,sy,ca,di,ox,sx,ag,cc,dr"
_PROBLEM_CATEGORY = "Problematic cell line"
_CAUTION_CATEGORY = "Caution"

_COMMERCIAL_PROVIDER_CATEGORY = "Cell line collections (Providers)"
_ID_BRIDGES = {"Cell_Model_Passport": "cell_model_passport", "DepMap": "depmap", "Cosmic": "cosmic"}


def _get(path: str, params: dict[str, str], timeout: int = 40) -> dict[str, object]:
    query = urllib.parse.urlencode(params)
    url = f"{API_BASE}/{path.lstrip('/')}?{query}"
    return cast(
        "dict[str, object]",
        http.get_json(url, headers={"Accept": "application/json"}, timeout=timeout),
    )


def _list(record: dict[str, object], key: str) -> list[dict[str, object]]:
    return cast("list[dict[str, object]]", record.get(key) or [])


def _cell_lines(payload: dict[str, object]) -> list[dict[str, object]]:
    cellosaurus = cast("dict[str, object]", payload.get("Cellosaurus") or {})
    return _list(cellosaurus, "cell-line-list")


def _primary_accession(record: dict[str, object]) -> str | None:
    accessions = _list(record, "accession-list")
    for entry in accessions:
        if entry.get("type") == "primary":
            return cast("str | None", entry.get("value"))
    return cast("str | None", accessions[0].get("value")) if accessions else None


def _names(record: dict[str, object]) -> list[str]:
    return [str(n.get("value")) for n in _list(record, "name-list") if n.get("value")]


def _comments(record: dict[str, object]) -> list[dict[str, str]]:
    return [
        {"category": str(c.get("category")), "value": str(c.get("value"))}
        for c in _list(record, "comment-list")
    ]


def _xrefs(record: dict[str, object]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for x in _list(record, "xref-list"):
        db = cast("str | None", x.get("database"))
        if db and db not in out:
            out[db] = {
                "accession": str(x.get("accession")),
                "url": str(x.get("url")),
                "category": str(x.get("category")),
            }
    return out


def _flatten(record: dict[str, object]) -> dict[str, object]:
    return {
        "accession": _primary_accession(record),
        "names": _names(record),
        "category": record.get("category"),
        "sex": record.get("sex"),
        "age": record.get("age"),
        "species": [s.get("label") for s in _list(record, "species-list") if s.get("label")],
        "diseases": [
            {
                "terminology": d.get("database"),
                "accession": d.get("accession"),
                "value": d.get("label"),
            }
            for d in _list(record, "disease-list")
        ],
        "comments": _comments(record),
        "xrefs": _xrefs(record),
    }


def get_cell_line(accession: str, fields: str = _COMPACT_FIELDS) -> dict[str, object] | None:
    payload = _get(f"cell-line/{accession}", {"format": "json", "fields": fields})
    records = _cell_lines(payload)
    return _flatten(records[0]) if records else None


def find_cell_line(name: str, fields: str = _COMPACT_FIELDS) -> dict[str, object] | None:
    payload = _get(
        "search/cell-line",
        {"q": f"id:{name}", "format": "json", "fields": fields, "rows": "10"},
    )
    records = _cell_lines(payload)
    if not records:
        return None
    lowered = name.strip().lower()
    for record in records:
        if any(n.strip().lower() == lowered for n in _names(record)):
            return _flatten(record)
    return _flatten(records[0])


def provenance(name: str) -> dict[str, object] | None:
    record = find_cell_line(name)
    if record is None:
        return None
    comments = cast("list[dict[str, str]]", record["comments"])
    problems = [c for c in comments if c["category"] == _PROBLEM_CATEGORY]
    cautions = [c["value"] for c in comments if c["category"] == _CAUTION_CATEGORY]
    xrefs = cast("dict[str, dict[str, str]]", record["xrefs"])
    commercial_listings = {
        db: CommercialListing(accession=entry["accession"], url=entry["url"])
        for db, entry in xrefs.items()
        if entry.get("category") == _COMMERCIAL_PROVIDER_CATEGORY and entry.get("url")
    }
    cross_ids = {alias: xrefs[db]["accession"] for db, alias in _ID_BRIDGES.items() if db in xrefs}
    accession = cast("str | None", record["accession"])
    return Provenance(
        found=True,
        accession=accession,
        names=cast("list[str]", record["names"]),
        category=cast("str | None", record["category"]),
        species=cast("list[str]", record["species"]),
        problematic=bool(problems),
        problems=[p["value"] for p in problems],
        cautions=cautions,
        provenance_ok=0.0 if problems else 1.0,
        commercial_listings=commercial_listings,
        cross_ids=cross_ids,
        cellosaurus_url=f"https://www.cellosaurus.org/{accession}" if accession else None,
    ).model_dump()


def models_for_disease(disease_term: str, rows: int = 1000) -> dict[str, object]:
    payload = _get(
        "search/cell-line",
        {"q": f'di:"{disease_term}"', "format": "json", "fields": "id,ac,ca,cc", "rows": str(rows)},
    )
    records = _cell_lines(payload)
    out: list[dict[str, object]] = []
    for record in records:
        problems = [c for c in _comments(record) if c["category"] == _PROBLEM_CATEGORY]
        names: list[str | None] = list(_names(record)) or [None]
        out.append(
            {
                "accession": _primary_accession(record),
                "name": names[0],
                "category": record.get("category"),
                "problematic": bool(problems),
            }
        )
    return {"disease": disease_term, "count": len(out), "models": out}


_CELLO_SEARCH_URL = f"{API_BASE}/search/cell-line"


def cello_models(disease_term: str, rows: int = 1000) -> list[CellModelHit]:
    qs = urllib.parse.urlencode(
        {
            "q": f'di:"{disease_term}"',
            "format": "json",
            "rows": str(rows),
            "fields": "id,ac,ca,cc,di",
        }
    )
    d = cast(
        "dict[str, object]",
        http.get_json(f"{_CELLO_SEARCH_URL}?{qs}", headers={"Accept": "application/json"}),
    )
    out: list[CellModelHit] = []
    cellosaurus = cast("dict[str, object]", d.get("Cellosaurus", {}))
    for c in cast("list[dict[str, object]]", cellosaurus.get("cell-line-list", [])):
        blob = json.dumps(c).lower()
        name_list = cast("list[dict[str, object]]", c.get("name-list") or [{}])
        raw_id = c.get("accession", c.get("id"))
        raw_name = c.get("name") or name_list[0].get("value")
        category = c.get("category")
        out.append(
            CellModelHit(
                id=str(raw_id) if raw_id is not None else None,
                name=str(raw_name) if raw_name is not None else None,
                category=str(category) if category is not None else None,
                problematic=("problematic" in blob or "misidentif" in blob),
            )
        )
    return out
