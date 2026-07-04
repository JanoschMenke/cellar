"""
Cell Model Passports (Wellcome Sanger Institute) — the curated hub behind the
Sanger Cancer Dependency Map. This is the real data source the retrieval layer's
old `depmap_stub` pointed at.

Public JSON:API 1.0 service, no authentication. Key facts, verified live:
  base            https://api.cellmodelpassports.sanger.ac.uk
  resources       /models (~2266), /genes (~45751), /samples, /patients,
                  /datasets/{mutations,fusions,proteomics,...}
  per-model data  /models/{SIDM}/datasets/{mutations|growth_rate|...} (nested)
  pagination      ?page[number]=N&page[size]=K  (large page sizes time out;
                  keep K <= ~100)
  filtering       flask-rest-jsonapi complex filter, NOT ?filter[key]=val (that
                  form is silently ignored). Pass a list of
                  {"name","op","val"} dicts, JSON-encoded into ?filter=...
                    names lookup: [{"name":"names","op":"any","val":"PANC-1"}]
                    gene symbol:  [{"name":"symbol","op":"eq","val":"ZDHHC20"}]
  includes        ?include=sample,identifiers -> a top-level `included` array

Reproducibility: responses are cached to disk keyed by request URL so demos run
offline once warmed (mirrors CLAUDE.md's reproducibility note). Set use_cache=False
to always hit the network.
"""
import hashlib
import json
import os
import urllib.parse
import urllib.request

API_BASE = "https://api.cellmodelpassports.sanger.ac.uk"
DEFAULT_CACHE_DIR = os.path.join(".cellar", "cmp_cache")
DEFAULT_PAGE_SIZE = 100
DEFAULT_MAX_PAGES = 25
_HEADERS = {"Accept": "application/vnd.api+json"}

Filter = dict[str, object]


def _build_url(
    path: str,
    filters: list[Filter] | None = None,
    include: list[str] | None = None,
    page_number: int | None = None,
    page_size: int | None = None,
) -> str:
    params: dict[str, str] = {}
    if filters:
        params["filter"] = json.dumps(filters, separators=(",", ":"))
    if include:
        params["include"] = ",".join(include)
    if page_number is not None:
        params["page[number]"] = str(page_number)
    if page_size is not None:
        params["page[size]"] = str(page_size)
    query = urllib.parse.urlencode(params)
    return f"{API_BASE}/{path.lstrip('/')}" + (f"?{query}" if query else "")


def _cache_file(url: str, cache_dir: str) -> str:
    digest = hashlib.sha256(url.encode()).hexdigest()[:32]
    return os.path.join(cache_dir, f"{digest}.json")


def _fetch(
    url: str,
    use_cache: bool = True,
    cache_dir: str = DEFAULT_CACHE_DIR,
    timeout: int = 60,
) -> dict[str, object]:
    cache_path = _cache_file(url, cache_dir)
    if use_cache and os.path.exists(cache_path):
        with open(cache_path) as f:
            return json.load(f)
    request = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode())
    if use_cache:
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(payload, f)
    return payload


def _relationship_ids(relationships: dict[str, object]) -> dict[str, object]:
    out: dict[str, object] = {}
    for name, rel in relationships.items():
        data = rel.get("data") if isinstance(rel, dict) else None
        if isinstance(data, list):
            out[name] = [d.get("id") for d in data]
        elif isinstance(data, dict):
            out[name] = data.get("id")
    return out


def _flatten(resource: dict[str, object]) -> dict[str, object]:
    flat: dict[str, object] = {"id": resource.get("id"), "type": resource.get("type")}
    flat.update(resource.get("attributes") or {})
    rels = _relationship_ids(resource.get("relationships") or {})
    if rels:
        flat["relationships"] = rels
    return flat


def _raise_on_errors(payload: dict[str, object], url: str) -> None:
    errors = payload.get("errors")
    if errors:
        first = errors[0] if isinstance(errors, list) and errors else {}
        detail = first.get("detail") or first.get("title") or "unknown error"
        raise RuntimeError(f"Cell Model Passports error for {url}: {detail}")


def get_one(
    path: str,
    include: list[str] | None = None,
    use_cache: bool = True,
    cache_dir: str = DEFAULT_CACHE_DIR,
) -> dict[str, object] | None:
    url = _build_url(path, include=include)
    payload = _fetch(url, use_cache=use_cache, cache_dir=cache_dir)
    _raise_on_errors(payload, url)
    data = payload.get("data")
    if not data:
        return None
    flat = _flatten(data)
    included = payload.get("included")
    if included:
        flat["included"] = [_flatten(r) for r in included]
    return flat


def get_collection(
    path: str,
    filters: list[Filter] | None = None,
    include: list[str] | None = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int = DEFAULT_MAX_PAGES,
    use_cache: bool = True,
    cache_dir: str = DEFAULT_CACHE_DIR,
) -> dict[str, object]:
    records: list[dict[str, object]] = []
    count: int | None = None
    pages_fetched = 0
    url: str | None = _build_url(
        path, filters=filters, include=include, page_number=1, page_size=page_size
    )
    while url and pages_fetched < max_pages:
        payload = _fetch(url, use_cache=use_cache, cache_dir=cache_dir)
        _raise_on_errors(payload, url)
        meta = payload.get("meta") or {}
        if count is None:
            count = meta.get("count")
        records.extend(_flatten(r) for r in payload.get("data") or [])
        pages_fetched += 1
        url = (payload.get("links") or {}).get("next")
    truncated = bool(url) or (count is not None and len(records) < count)
    return {
        "count": count,
        "records": records,
        "pages_fetched": pages_fetched,
        "truncated": truncated,
    }


# ---------------------------------------------------------------- models
def list_models(
    filters: list[Filter] | None = None,
    include: list[str] | None = None,
    **kwargs: object,
) -> dict[str, object]:
    return get_collection("models", filters=filters, include=include, **kwargs)


def get_model(
    sidm_id: str, include: list[str] | None = None, **kwargs: object
) -> dict[str, object] | None:
    return get_one(f"models/{sidm_id}", include=include, **kwargs)


def _name_variants(name: str) -> list[str]:
    variants = [name, name.replace(" ", "-"), name.replace("-", " "), name.replace(" ", ""), name.replace("-", "")]
    seen: set[str] = set()
    return [v for v in variants if not (v in seen or seen.add(v))]


def find_model(name: str, include: list[str] | None = None, **kwargs: object) -> dict[str, object] | None:
    """Resolve a cell-line name to its model, tolerating punctuation differences
    (CMP stores e.g. 'MIA-PaCa-2', not 'MIA PaCa-2'). Tries the name as given,
    then hyphen/space variants; returns the first match or None."""
    for variant in _name_variants(name):
        result = list_models(
            filters=[{"name": "names", "op": "any", "val": variant}],
            include=include,
            page_size=5,
            max_pages=1,
            **kwargs,
        )
        records = result["records"]
        if records:
            return records[0]
    return None


# ---------------------------------------------------------------- genes
def list_genes(filters: list[Filter] | None = None, **kwargs: object) -> dict[str, object]:
    return get_collection("genes", filters=filters, **kwargs)


def get_gene(sidg_id: str, **kwargs: object) -> dict[str, object] | None:
    return get_one(f"genes/{sidg_id}", **kwargs)


def find_gene(symbol: str, **kwargs: object) -> dict[str, object] | None:
    result = list_genes(
        filters=[{"name": "symbol", "op": "eq", "val": symbol}],
        page_size=5,
        max_pages=1,
        **kwargs,
    )
    records = result["records"]
    return records[0] if records else None


# ---------------------------------------------------------------- samples / patients
def get_sample(sids_id: str, **kwargs: object) -> dict[str, object] | None:
    return get_one(f"samples/{sids_id}", **kwargs)


def list_samples(filters: list[Filter] | None = None, **kwargs: object) -> dict[str, object]:
    return get_collection("samples", filters=filters, **kwargs)


def get_patient(sidp_id: str, **kwargs: object) -> dict[str, object] | None:
    return get_one(f"patients/{sidp_id}", **kwargs)


def list_patients(filters: list[Filter] | None = None, **kwargs: object) -> dict[str, object]:
    return get_collection("patients", filters=filters, **kwargs)


# ---------------------------------------------------------------- datasets (per model)
def model_dataset(
    sidm_id: str,
    dataset: str,
    filters: list[Filter] | None = None,
    max_pages: int = DEFAULT_MAX_PAGES,
    **kwargs: object,
) -> dict[str, object]:
    return get_collection(
        f"models/{sidm_id}/datasets/{dataset}",
        filters=filters,
        max_pages=max_pages,
        **kwargs,
    )


def model_gene_mutations(
    sidm_id: str, gene_symbol: str, **kwargs: object
) -> dict[str, object]:
    gene = find_gene(gene_symbol, **kwargs)
    if gene is None:
        return {"count": 0, "records": [], "pages_fetched": 0, "truncated": False}
    return model_dataset(
        sidm_id,
        "mutations",
        filters=[{"name": "gene_id", "op": "eq", "val": gene["id"]}],
        max_pages=3,
        **kwargs,
    )


# ---------------------------------------------------------------- matchmaker facts
_DATASET_FLAGS = {
    "mutations_available": "mutations",
    "cnv_available": "cnv",
    "expression_available": "expression",
    "rnaseq_available": "rnaseq",
    "proteomics_available": "proteomics",
    "fusions_available": "fusions",
    "methylation_available": "methylation",
    "crispr_ko_available": "crispr_ko",
    "drugs_available": "drugs",
}


def model_facts(name: str, **kwargs: object) -> dict[str, object] | None:
    """Compact, matchmaker-facing fact sheet for a cell line by name. Returns None
    if the model is not in Cell Model Passports (e.g. an organoid/GEMM built by a
    CRO). Replaces retrieval.depmap_stub with real Sanger DepMap model facts."""
    model = find_model(name, **kwargs)
    if model is None:
        return None
    available = [ds for flag, ds in _DATASET_FLAGS.items() if model.get(flag)]
    sidm_id = model["id"]
    return {
        "sidm_id": sidm_id,
        "names": model.get("names"),
        "model_type": model.get("model_type"),
        "growth_properties": model.get("growth_properties"),
        "ploidy": model.get("ploidy"),
        "mutations_per_mb": model.get("mutations_per_mb"),
        "crispr_ko_available": bool(model.get("crispr_ko_available")),
        "datasets_available": available,
        "catalog_url": f"https://cellmodelpassports.sanger.ac.uk/passports/{sidm_id}",
    }
