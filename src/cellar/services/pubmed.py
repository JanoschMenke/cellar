import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree

_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _fetch(url: str, timeout: int = 30) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def _esearch(query: str, max_results: int, sort: str) -> dict[str, object]:
    import json

    url = f"{_EUTILS}/esearch.fcgi?" + urllib.parse.urlencode(
        {
            "db": "pubmed",
            "term": query,
            "retmax": str(max_results),
            "retmode": "json",
            "sort": sort or "relevance",
        }
    )
    result = json.loads(_fetch(url).decode()).get("esearchresult", {})
    return {
        "pmids": list(result.get("idlist", [])),
        "total_count": int(result.get("count", 0) or 0),
    }


def _article_text(element: ElementTree.Element, path: str) -> str:
    return " ".join(node.text or "" for node in element.iterfind(path)).strip()


def _efetch(pmids: list[str]) -> dict[str, object]:
    if not pmids:
        return {"articles": []}
    url = f"{_EUTILS}/efetch.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}
    )
    root = ElementTree.fromstring(_fetch(url))
    articles: list[dict[str, object]] = []
    for citation in root.iterfind(".//PubmedArticle"):
        pmid = _article_text(citation, ".//MedlineCitation/PMID")
        doi = ""
        for article_id in citation.iterfind(".//ArticleIdList/ArticleId"):
            if article_id.get("IdType") == "doi":
                doi = article_id.text or ""
        articles.append(
            {
                "identifiers": {"pmid": pmid, "doi": doi},
                "title": _article_text(citation, ".//Article/ArticleTitle"),
                "abstract": _article_text(citation, ".//Abstract/AbstractText"),
            }
        )
    return {"articles": articles}


def pubmed_mcp(server: str, action: str, **kwargs: object) -> dict[str, object]:
    if action == "search_articles":
        return _esearch(
            str(kwargs.get("query", "")),
            int(kwargs.get("max_results", 6) or 6),
            str(kwargs.get("sort", "relevance")),
        )
    if action == "get_article_metadata":
        pmids = [str(p) for p in (kwargs.get("pmids") or [])]
        return _efetch(pmids)
    return {}
