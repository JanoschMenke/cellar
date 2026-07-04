"""
Elicit — semantic search over 138M+ academic papers. This is the wedge for cases
like ZDHHC20/PDAC where structured databases show ~0 target-disease association
but the primary literature is rich: Open Targets and STRING give scores and
edges, Elicit gives the actual papers behind (or missing behind) them.

API reference: https://docs.elicit.com/. Requires an API key on a paid Elicit
plan (Pro/Scale/Enterprise) with API access enabled, passed as
`Authorization: Bearer elk_live_...`. Read from the ELICIT_API_KEY environment
variable — never hardcode it.

Scope note: Elicit also offers a Reports and a Systematic Reviews pipeline
(POST /api/v1/reports, POST /api/v1/systematic-reviews) that can extract
structured columns across many papers — a good fit for the "prior model use"
and "model caveats" dimensions this module's docstring used to describe. Both
are ASYNC and take 5-15+ minutes (create -> poll -> result), which does not fit
a single synchronous agent tool-call turn in this codebase's manual loop
(agents/console_agent.py blocks until end_turn). They are intentionally not
implemented here; a real integration needs a background job + polling
architecture (e.g. a workspace-backed task the agent can check back on across
turns), not a tool call. The fast, synchronous /api/v1/search endpoint below is
what fits today's agent loop.
"""
import json
import os
import urllib.error
import urllib.request

API_BASE = "https://elicit.com"
SEARCH_PATH = "/api/v1/search"
_MAX_RESULTS_CAP = 100


def _api_key() -> str:
    api_key = os.environ.get("ELICIT_API_KEY")
    if not api_key:
        raise RuntimeError("ELICIT_API_KEY is not set — Elicit requires a paid API key.")
    return api_key


def _post(path: str, body: dict[str, object], timeout: int = 40) -> dict[str, object]:
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {_api_key()}",
            "User-Agent": "cellar-matchmaker/1.0 (+https://github.com/JanoschMenke/cellar)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        if error.code in (401, 403):
            raise RuntimeError(f"Elicit auth failed ({error.code}): check ELICIT_API_KEY. {detail}") from error
        if error.code == 429:
            raise RuntimeError(f"Elicit rate limit hit (429): {detail}") from error
        raise RuntimeError(f"Elicit error ({error.code}): {detail}") from error


def _flatten_paper(paper: dict[str, object]) -> dict[str, object]:
    return {
        "elicit_id": paper.get("elicitId"),
        "title": paper.get("title"),
        "authors": paper.get("authors"),
        "year": paper.get("year"),
        "abstract": paper.get("abstract"),
        "doi": paper.get("doi"),
        "pmid": paper.get("pmid"),
        "venue": paper.get("venue"),
        "cited_by_count": paper.get("citedByCount"),
        "urls": paper.get("urls"),
    }


def search_literature(
    query: str,
    max_results: int = 10,
    min_year: int | None = None,
    max_year: int | None = None,
    include_keywords: list[str] | None = None,
    exclude_keywords: list[str] | None = None,
    type_tags: list[str] | None = None,
    pubmed_only: bool = False,
    exclude_retracted: bool = True,
) -> dict[str, object]:
    """Semantic search over Elicit's paper corpus. type_tags examples: 'RCT',
    'Meta-Analysis', 'Systematic Review', 'Observational Study'. Returns papers
    with title/authors/year/abstract/doi/pmid/venue/citation count/urls — the
    citable evidence a judge can quote, not just a relevance score."""
    filters: dict[str, object] = {}
    if min_year is not None:
        filters["minYear"] = min_year
    if max_year is not None:
        filters["maxYear"] = max_year
    if include_keywords:
        filters["includeKeywords"] = include_keywords
    if exclude_keywords:
        filters["excludeKeywords"] = exclude_keywords
    if type_tags:
        filters["typeTags"] = type_tags
    if pubmed_only:
        filters["pubmedOnly"] = True
    if exclude_retracted:
        filters["retracted"] = "exclude_retracted"

    body: dict[str, object] = {
        "query": query,
        "corpus": "elicit",
        "searchMode": "semantic",
        "maxResults": min(max_results, _MAX_RESULTS_CAP),
    }
    if filters:
        body["filters"] = filters

    data = _post(SEARCH_PATH, body)
    papers = [_flatten_paper(p) for p in data.get("papers", [])]
    return {
        "found": True,
        "query": query,
        "n_results": len(papers),
        "papers": papers,
        "warnings": data.get("warnings", []),
    }
