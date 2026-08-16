import hashlib
import json
import os
import urllib.parse
from typing import cast

from cellar.config import CELL_MODEL_PASSPORTS_URL as API_BASE
from cellar.config import CMP_ACCEPT_HEADER as _ACCEPT_HEADER
from cellar.config import CMP_DEFAULT_MAX_PAGES as DEFAULT_MAX_PAGES
from cellar.config import CMP_DEFAULT_PAGE_SIZE as DEFAULT_PAGE_SIZE
from cellar.schemas.sources import ModelFacts
from cellar.utils import http

DEFAULT_CACHE_DIR = os.path.join(".cellar", "cmp_cache")
_HEADERS = {"Accept": _ACCEPT_HEADER}

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
            return cast("dict[str, object]", json.load(f))
    payload = cast("dict[str, object]", http.get_json(url, headers=_HEADERS, timeout=timeout))
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
            out[name] = [d.get("id") if isinstance(d, dict) else None for d in data]
        elif isinstance(data, dict):
            out[name] = data.get("id")
    return out


def _flatten(resource: dict[str, object]) -> dict[str, object]:
    flat: dict[str, object] = {"id": resource.get("id"), "type": resource.get("type")}
    flat.update(cast("dict[str, object]", resource.get("attributes") or {}))
    rels = _relationship_ids(cast("dict[str, object]", resource.get("relationships") or {}))
    if rels:
        flat["relationships"] = rels
    return flat


def _raise_on_errors(payload: dict[str, object], url: str) -> None:
    errors = payload.get("errors")
    if errors:
        first = cast("dict[str, object]", errors[0]) if isinstance(errors, list) and errors else {}
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
    flat = _flatten(cast("dict[str, object]", data))
    included = cast("list[object] | None", payload.get("included"))
    if included:
        flat["included"] = [_flatten(cast("dict[str, object]", r)) for r in included]
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
        meta = cast("dict[str, object]", payload.get("meta") or {})
        if count is None:
            count = cast("int | None", meta.get("count"))
        data = cast("list[dict[str, object]]", payload.get("data") or [])
        records.extend(_flatten(r) for r in data)
        pages_fetched += 1
        links = cast("dict[str, object]", payload.get("links") or {})
        url = cast("str | None", links.get("next"))
    truncated = bool(url) or (count is not None and len(records) < count)
    return {
        "count": count,
        "records": records,
        "pages_fetched": pages_fetched,
        "truncated": truncated,
    }


def list_models(
    filters: list[Filter] | None = None,
    include: list[str] | None = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int = DEFAULT_MAX_PAGES,
    use_cache: bool = True,
    cache_dir: str = DEFAULT_CACHE_DIR,
) -> dict[str, object]:
    return get_collection(
        "models",
        filters=filters,
        include=include,
        page_size=page_size,
        max_pages=max_pages,
        use_cache=use_cache,
        cache_dir=cache_dir,
    )


def get_model(
    sidm_id: str,
    include: list[str] | None = None,
    use_cache: bool = True,
    cache_dir: str = DEFAULT_CACHE_DIR,
) -> dict[str, object] | None:
    return get_one(f"models/{sidm_id}", include=include, use_cache=use_cache, cache_dir=cache_dir)


def _name_variants(name: str) -> list[str]:
    variants = [
        name,
        name.replace(" ", "-"),
        name.replace("-", " "),
        name.replace(" ", ""),
        name.replace("-", ""),
    ]
    seen: set[str] = set()
    unique: list[str] = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            unique.append(v)
    return unique


def find_model(
    name: str,
    include: list[str] | None = None,
    use_cache: bool = True,
    cache_dir: str = DEFAULT_CACHE_DIR,
) -> dict[str, object] | None:
    for variant in _name_variants(name):
        result = list_models(
            filters=[{"name": "names", "op": "any", "val": variant}],
            include=include,
            page_size=5,
            max_pages=1,
            use_cache=use_cache,
            cache_dir=cache_dir,
        )
        records = cast("list[dict[str, object]]", result["records"])
        if records:
            return records[0]
    return None


def list_genes(
    filters: list[Filter] | None = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int = DEFAULT_MAX_PAGES,
    use_cache: bool = True,
    cache_dir: str = DEFAULT_CACHE_DIR,
) -> dict[str, object]:
    return get_collection(
        "genes",
        filters=filters,
        page_size=page_size,
        max_pages=max_pages,
        use_cache=use_cache,
        cache_dir=cache_dir,
    )


def get_gene(
    sidg_id: str, use_cache: bool = True, cache_dir: str = DEFAULT_CACHE_DIR
) -> dict[str, object] | None:
    return get_one(f"genes/{sidg_id}", use_cache=use_cache, cache_dir=cache_dir)


def find_gene(
    symbol: str, use_cache: bool = True, cache_dir: str = DEFAULT_CACHE_DIR
) -> dict[str, object] | None:
    result = list_genes(
        filters=[{"name": "symbol", "op": "eq", "val": symbol}],
        page_size=5,
        max_pages=1,
        use_cache=use_cache,
        cache_dir=cache_dir,
    )
    records = cast("list[dict[str, object]]", result["records"])
    return records[0] if records else None


def get_sample(
    sids_id: str, use_cache: bool = True, cache_dir: str = DEFAULT_CACHE_DIR
) -> dict[str, object] | None:
    return get_one(f"samples/{sids_id}", use_cache=use_cache, cache_dir=cache_dir)


def list_samples(
    filters: list[Filter] | None = None,
    use_cache: bool = True,
    cache_dir: str = DEFAULT_CACHE_DIR,
) -> dict[str, object]:
    return get_collection("samples", filters=filters, use_cache=use_cache, cache_dir=cache_dir)


def get_patient(
    sidp_id: str, use_cache: bool = True, cache_dir: str = DEFAULT_CACHE_DIR
) -> dict[str, object] | None:
    return get_one(f"patients/{sidp_id}", use_cache=use_cache, cache_dir=cache_dir)


def list_patients(
    filters: list[Filter] | None = None,
    use_cache: bool = True,
    cache_dir: str = DEFAULT_CACHE_DIR,
) -> dict[str, object]:
    return get_collection("patients", filters=filters, use_cache=use_cache, cache_dir=cache_dir)


def model_dataset(
    sidm_id: str,
    dataset: str,
    filters: list[Filter] | None = None,
    max_pages: int = DEFAULT_MAX_PAGES,
    use_cache: bool = True,
    cache_dir: str = DEFAULT_CACHE_DIR,
) -> dict[str, object]:
    return get_collection(
        f"models/{sidm_id}/datasets/{dataset}",
        filters=filters,
        max_pages=max_pages,
        use_cache=use_cache,
        cache_dir=cache_dir,
    )


def model_gene_mutations(
    sidm_id: str,
    gene_symbol: str,
    use_cache: bool = True,
    cache_dir: str = DEFAULT_CACHE_DIR,
) -> dict[str, object]:
    gene = find_gene(gene_symbol, use_cache=use_cache, cache_dir=cache_dir)
    if gene is None:
        return {"count": 0, "records": [], "pages_fetched": 0, "truncated": False}
    return model_dataset(
        sidm_id,
        "mutations",
        filters=[{"name": "gene_id", "op": "eq", "val": gene["id"]}],
        max_pages=3,
        use_cache=use_cache,
        cache_dir=cache_dir,
    )


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


def model_facts(
    name: str, use_cache: bool = True, cache_dir: str = DEFAULT_CACHE_DIR
) -> dict[str, object] | None:
    model = find_model(name, use_cache=use_cache, cache_dir=cache_dir)
    if model is None:
        return None
    available = [ds for flag, ds in _DATASET_FLAGS.items() if model.get(flag)]
    sidm_id = str(model["id"])
    return ModelFacts(
        sidm_id=sidm_id,
        names=cast("list[str] | None", model.get("names")),
        model_type=cast("str | None", model.get("model_type")),
        growth_properties=cast("str | None", model.get("growth_properties")),
        ploidy=cast("float | None", model.get("ploidy")),
        mutations_per_mb=cast("float | None", model.get("mutations_per_mb")),
        crispr_ko_available=bool(model.get("crispr_ko_available")),
        datasets_available=available,
        catalog_url=f"https://cellmodelpassports.sanger.ac.uk/passports/{sidm_id}",
    ).model_dump()
