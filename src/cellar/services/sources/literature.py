import urllib.parse
from typing import cast

from cellar.config import EUROPE_PMC_MAX_RESULTS as _MAX_RESULTS_CAP
from cellar.config import EUROPE_PMC_SEARCH_URL as _SEARCH_URL
from cellar.config import HTTP_USER_AGENT as _USER_AGENT
from cellar.utils import http


def _build_query(query: str, min_year: int | None) -> str:
    if min_year is not None:
        return f"({query}) AND FIRST_PDATE:[{min_year}-01-01 TO 3000-12-31]"
    return query


def _get(url: str, timeout: int = 40) -> dict[str, object]:
    try:
        return cast(
            "dict[str, object]",
            http.get_json(
                url,
                headers={"Accept": "application/json", "User-Agent": _USER_AGENT},
                timeout=timeout,
            ),
        )
    except http.HttpError as error:
        raise RuntimeError(f"Europe PMC error ({error.status}): {error.body}") from error


def _to_int(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _flatten(record: dict[str, object]) -> dict[str, object]:
    pmid = record.get("pmid")
    doi = record.get("doi")
    url = (
        f"https://doi.org/{doi}"
        if doi
        else (f"https://europepmc.org/abstract/MED/{pmid}" if pmid else None)
    )
    return {
        "title": record.get("title"),
        "authors": record.get("authorString"),
        "year": _to_int(record.get("pubYear")),
        "abstract": record.get("abstractText"),
        "doi": doi,
        "pmid": pmid,
        "venue": record.get("journalTitle"),
        "cited_by_count": _to_int(record.get("citedByCount")) or 0,
        "is_preprint": record.get("source") == "PPR",
        "url": url,
    }


def search_literature(
    query: str,
    max_results: int = 10,
    min_year: int | None = None,
) -> dict[str, object]:
    params = urllib.parse.urlencode(
        {
            "query": _build_query(query, min_year),
            "format": "json",
            "resultType": "core",
            "pageSize": min(max_results, _MAX_RESULTS_CAP),
        }
    )
    data = _get(f"{_SEARCH_URL}?{params}")
    result_list = data.get("resultList") or {}
    records = result_list.get("result") or [] if isinstance(result_list, dict) else []
    papers = [_flatten(record) for record in records]
    return {
        "found": True,
        "query": query,
        "n_results": len(papers),
        "papers": papers,
    }
