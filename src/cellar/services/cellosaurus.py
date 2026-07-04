"""
Cellosaurus (ELIXIR / SIB) — the authority on cell-line IDENTITY, PROVENANCE and
cross-references. In the matchmaker it answers two dimensions no other source
owns as well:

  * provenance & reliability — is this line problematic (misidentified /
    contaminated / from another species)? Cellosaurus flags these explicitly with
    a "Problematic cell line" comment. Feeds the `provenance_ok` score.
  * identity bridge + commercial sourcing — a name resolves to a stable CVCL
    accession plus cross-references. Each xref carries a `category`; entries
    tagged "Cell line collections (Providers)" are commercial/biobank suppliers
    and — verified live — each carries a direct, ready-to-click product-page
    `url` (e.g. ATCC -> https://www.atcc.org/products/CRL-1469), not just a
    catalogue accession. Filtering by that category (rather than a hardcoded
    supplier name list) picks up every provider Cellosaurus tracks, including
    regional biobanks (BCRC, RCB, KCLB, …) we would otherwise miss. Other xrefs
    bridge to our own sources (Cell_Model_Passport -> SIDM, DepMap -> ACH).

Public REST API, no auth. Verified live:
  base     https://api.cellosaurus.org
  single   /cell-line/{accession}?format=json&fields=...   (e.g. CVCL_0480 = PANC-1)
  search   /search/cell-line?q=...&format=json&fields=...&rows=...
           name resolves via q=id:<name>; exact name is matched from name-list.
  problematic flag: a comment with category == "Problematic cell line".
"""
import json
import urllib.parse
import urllib.request

API_BASE = "https://api.cellosaurus.org"
_COMPACT_FIELDS = "id,ac,sy,ca,di,ox,sx,ag,cc,dr"
_PROBLEM_CATEGORY = "Problematic cell line"
_CAUTION_CATEGORY = "Caution"

# The xref category Cellosaurus uses for commercial/biobank suppliers (ATCC,
# ECACC, DSMZ, and ~15 more regional providers) — each carries a direct url.
_COMMERCIAL_PROVIDER_CATEGORY = "Cell line collections (Providers)"
# Cross-reference databases that bridge to our other sources.
_ID_BRIDGES = {"Cell_Model_Passport": "cell_model_passport", "DepMap": "depmap", "Cosmic": "cosmic"}


def _get(path: str, params: dict[str, str], timeout: int = 40) -> dict[str, object]:
    query = urllib.parse.urlencode(params)
    url = f"{API_BASE}/{path.lstrip('/')}?{query}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def _cell_lines(payload: dict[str, object]) -> list[dict[str, object]]:
    return (payload.get("Cellosaurus") or {}).get("cell-line-list") or []


def _primary_accession(record: dict[str, object]) -> str | None:
    for entry in record.get("accession-list") or []:
        if entry.get("type") == "primary":
            return entry.get("value")
    accessions = record.get("accession-list") or []
    return accessions[0].get("value") if accessions else None


def _names(record: dict[str, object]) -> list[str]:
    return [n.get("value") for n in record.get("name-list") or [] if n.get("value")]


def _comments(record: dict[str, object]) -> list[dict[str, str]]:
    return [
        {"category": c.get("category"), "value": c.get("value")}
        for c in record.get("comment-list") or []
    ]


def _xrefs(record: dict[str, object]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for x in record.get("xref-list") or []:
        db = x.get("database")
        if db and db not in out:
            out[db] = {
                "accession": x.get("accession"),
                "url": x.get("url"),
                "category": x.get("category"),
            }
    return out


def _flatten(record: dict[str, object]) -> dict[str, object]:
    return {
        "accession": _primary_accession(record),
        "names": _names(record),
        "category": record.get("category"),
        "sex": record.get("sex"),
        "age": record.get("age"),
        "species": [s.get("label") for s in record.get("species-list") or [] if s.get("label")],
        "diseases": [
            {"terminology": d.get("database"), "accession": d.get("accession"), "value": d.get("label")}
            for d in record.get("disease-list") or []
        ],
        "comments": _comments(record),
        "xrefs": _xrefs(record),
    }


def get_cell_line(accession: str, fields: str = _COMPACT_FIELDS) -> dict[str, object] | None:
    payload = _get(f"cell-line/{accession}", {"format": "json", "fields": fields})
    records = _cell_lines(payload)
    return _flatten(records[0]) if records else None


def find_cell_line(name: str, fields: str = _COMPACT_FIELDS) -> dict[str, object] | None:
    """Resolve a cell-line name to its Cellosaurus record. Searches by identifier
    and prefers an exact (case-insensitive) name match, else the top hit."""
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
    """Identity + provenance + sourcing summary for a cell line by name. Returns
    None if the name is not in Cellosaurus."""
    record = find_cell_line(name)
    if record is None:
        return None
    problems = [c for c in record["comments"] if c["category"] == _PROBLEM_CATEGORY]
    cautions = [c["value"] for c in record["comments"] if c["category"] == _CAUTION_CATEGORY]
    xrefs = record["xrefs"]
    commercial_listings = {
        db: {"accession": entry["accession"], "url": entry["url"]}
        for db, entry in xrefs.items()
        if entry.get("category") == _COMMERCIAL_PROVIDER_CATEGORY and entry.get("url")
    }
    cross_ids = {alias: xrefs[db]["accession"] for db, alias in _ID_BRIDGES.items() if db in xrefs}
    accession = record["accession"]
    return {
        "found": True,
        "accession": accession,
        "names": record["names"],
        "category": record["category"],
        "species": record["species"],
        "problematic": bool(problems),
        "problems": [p["value"] for p in problems],
        "cautions": cautions,
        "provenance_ok": 0.0 if problems else 1.0,
        "commercial_listings": commercial_listings,
        "cross_ids": cross_ids,
        "cellosaurus_url": f"https://www.cellosaurus.org/{accession}" if accession else None,
    }


def models_for_disease(disease_term: str, rows: int = 1000) -> dict[str, object]:
    """All Cellosaurus cell lines annotated to a disease, each with a problematic
    flag. The richer sibling of retrieval.cello_models used for candidate panels."""
    payload = _get(
        "search/cell-line",
        {"q": f'di:"{disease_term}"', "format": "json", "fields": "id,ac,ca,cc", "rows": str(rows)},
    )
    records = _cell_lines(payload)
    out = []
    for record in records:
        problems = [c for c in _comments(record) if c["category"] == _PROBLEM_CATEGORY]
        out.append(
            {
                "accession": _primary_accession(record),
                "name": (_names(record) or [None])[0],
                "category": record.get("category"),
                "problematic": bool(problems),
            }
        )
    return {"disease": disease_term, "count": len(out), "models": out}
