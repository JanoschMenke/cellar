import json
from types import SimpleNamespace
from typing import Any, cast

from cellar.agents.streaming_agent import StreamingAgent
from cellar.config import Settings
from cellar.schemas.events import StreamEventKind


def _agent() -> StreamingAgent:
    return StreamingAgent(client=cast(Any, object()), settings=Settings(), tools=[])


def _search_result(url: str, title: str) -> SimpleNamespace:
    return SimpleNamespace(type="web_search_result", url=url, title=title)


def _response(*blocks: object) -> Any:
    return SimpleNamespace(content=list(blocks))


def test_web_search_results_become_a_server_tool_result_event() -> None:
    response = _response(
        SimpleNamespace(type="text", text="ignored"),
        SimpleNamespace(
            type="web_search_tool_result",
            content=[
                _search_result("https://www.stemcell.com/intesticult.html", "IntestiCult"),
                _search_result("https://hub4organoids.eu/", "Hubrecht Organoid Technology"),
            ],
        ),
    )

    events = list(_agent()._emit_server_tool_results(response))

    assert len(events) == 1
    assert events[0].kind is StreamEventKind.SERVER_TOOL_RESULT
    assert events[0].tool_name == "web_search"
    payload = json.loads(events[0].content or "{}")
    assert payload["n_results"] == 2
    assert payload["results"][0]["url"] == "https://www.stemcell.com/intesticult.html"
    assert payload["results"][1]["title"] == "Hubrecht Organoid Technology"


def test_web_search_results_are_recorded_in_the_evidence_store() -> None:
    agent = _agent()
    response = _response(
        SimpleNamespace(
            type="web_search_tool_result",
            content=[_search_result("https://example.org/a", "A")],
        )
    )

    list(agent._emit_server_tool_results(response))

    records = agent.evidence_store.by_tool("web_search")
    assert len(records) == 1
    assert cast("dict[str, Any]", records[0].data)["results"][0]["url"] == "https://example.org/a"


def test_a_failed_web_search_is_reported_as_an_error() -> None:
    response = _response(
        SimpleNamespace(
            type="web_search_tool_result",
            content=SimpleNamespace(type="web_search_tool_result_error", error_code="max_uses"),
        )
    )

    events = list(_agent()._emit_server_tool_results(response))

    assert events[0].is_error is True
    assert json.loads(events[0].content or "{}")["error_code"] == "max_uses"


def test_results_without_a_url_are_skipped() -> None:
    response = _response(
        SimpleNamespace(
            type="web_search_tool_result",
            content=[_search_result("", "no url"), _search_result("https://example.org/b", "B")],
        )
    )

    payload = json.loads(list(_agent()._emit_server_tool_results(response))[0].content or "{}")

    assert payload["n_results"] == 1
    assert payload["results"][0]["url"] == "https://example.org/b"


def test_a_response_with_no_server_tool_blocks_emits_nothing() -> None:
    response = _response(SimpleNamespace(type="text", text="hello"))

    assert list(_agent()._emit_server_tool_results(response)) == []
