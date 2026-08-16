import json
from unittest.mock import patch

from cellar.services.sources import pubmed

_SAMPLE_XML = """<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345</PMID>
      <Article>
        <ArticleTitle>Title text</ArticleTitle>
        <Abstract><AbstractText>Abstract text</AbstractText></Abstract>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="doi">10.1/xyz</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""


def test_esearch_parses_json_bytes_from_http_get_bytes() -> None:
    payload = {"esearchresult": {"idlist": ["1", "2"], "count": "2"}}
    with patch.object(
        pubmed.http, "get_bytes", return_value=json.dumps(payload).encode()
    ) as mock_get_bytes:
        result = pubmed._esearch("brca1", 6, "relevance")

    assert result == {"pmids": ["1", "2"], "total_count": 2}
    mock_get_bytes.assert_called_once()
    _args, kwargs = mock_get_bytes.call_args
    assert kwargs == {"timeout": 30}


def test_efetch_parses_xml_bytes_from_http_get_bytes() -> None:
    with patch.object(
        pubmed.http, "get_bytes", return_value=_SAMPLE_XML.encode()
    ) as mock_get_bytes:
        result = pubmed._efetch(["12345"])

    assert result == {
        "articles": [
            {
                "identifiers": {"pmid": "12345", "doi": "10.1/xyz"},
                "title": "Title text",
                "abstract": "Abstract text",
            }
        ]
    }
    mock_get_bytes.assert_called_once()
    _args, kwargs = mock_get_bytes.call_args
    assert kwargs == {"timeout": 30}


def test_efetch_with_no_pmids_returns_empty_without_network() -> None:
    with patch.object(pubmed.http, "get_bytes") as mock_get_bytes:
        result = pubmed._efetch([])

    assert result == {"articles": []}
    mock_get_bytes.assert_not_called()
