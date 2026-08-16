from types import SimpleNamespace
from typing import Any, cast

from pydantic import BaseModel

from cellar.agents.verifier_agent import VerifierAgent, _digest
from cellar.config import Settings
from cellar.schemas.events import StreamEventKind
from cellar.schemas.tool_names import VERIFIER_EXCLUDED_TOOLS, ToolName
from cellar.schemas.verification import VerificationStatus
from cellar.services.evidence_store import EvidenceStore
from cellar.tools.base import Tool, ToolResult


class _EmptyInput(BaseModel):
    pass


class _DummyTool(Tool[_EmptyInput]):
    input_model = _EmptyInput

    def __init__(self, name: ToolName) -> None:
        self.name = name
        self.description = "dummy"

    def run(self, arguments: _EmptyInput) -> ToolResult:
        return ToolResult(content="{}")


def _all_tools() -> list[Tool[_EmptyInput]]:
    return [_DummyTool(member) for member in ToolName]


def test_verifier_excludes_exactly_the_panel_mutating_tools() -> None:
    agent = VerifierAgent(
        client=cast(Any, object()),
        settings=Settings(),
        tools=_all_tools(),
        evidence_store=EvidenceStore(),
    )

    assert set(agent._tools_by_name) == set(ToolName) - VERIFIER_EXCLUDED_TOOLS
    assert {
        ToolName.BUILD_RECOMMENDATIONS,
        ToolName.RECOMMEND_MODELS,
        ToolName.ANNOTATE_RECOMMENDATIONS,
        ToolName.PROPOSE_MODEL_CANDIDATE,
    } == VERIFIER_EXCLUDED_TOOLS


def test_digest_finds_latest_recommendation_via_tool_name() -> None:
    store = EvidenceStore()
    store.record(
        ToolName.BUILD_RECOMMENDATIONS,
        {},
        {"verdict": "ok", "cards": [{"model_name": "HEK293", "recommended": True}]},
    )

    digest = _digest(store)

    assert "Recommendation to verify" in digest
    assert "HEK293" in digest


def test_digest_falls_back_to_recommend_models_record() -> None:
    store = EvidenceStore()
    store.record(
        ToolName.RECOMMEND_MODELS,
        {},
        {"verdict": "ok", "cards": [{"model_name": "MIA-PaCa-2", "recommended": True}]},
    )

    digest = _digest(store)

    assert "Recommendation to verify" in digest
    assert "MIA-PaCa-2" in digest


def test_digest_reports_when_no_recommendation_yet() -> None:
    digest = _digest(EvidenceStore())

    assert "No recommendation has been produced yet." in digest


def _text_delta(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        type="content_block_delta", delta=SimpleNamespace(type="text_delta", text=text)
    )


def _final_message(content: list[object], stop_reason: str) -> SimpleNamespace:
    return SimpleNamespace(content=content, stop_reason=stop_reason)


class _FakeStream:
    def __init__(self, events: list[object], final: SimpleNamespace) -> None:
        self._events = events
        self._final = final

    def __enter__(self) -> "_FakeStream":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def __iter__(self) -> Any:
        return iter(self._events)

    def get_final_message(self) -> SimpleNamespace:
        return self._final


class _FakeMessages:
    def __init__(self, scripted: list[_FakeStream]) -> None:
        self._scripted = scripted
        self._i = 0

    def stream(self, **kwargs: object) -> _FakeStream:
        stream = self._scripted[self._i]
        self._i += 1
        return stream


class _FakeClient:
    def __init__(self, scripted: list[_FakeStream]) -> None:
        self.messages = _FakeMessages(scripted)


def test_verify_yields_exactly_one_verify_result_and_no_text_event() -> None:
    verdict = "Verified: sound\n\n- Checked the top pick's dependency evidence."
    final = _final_message([_text_delta(verdict[:10]), _text_delta(verdict[10:])], "end_turn")
    client = cast(
        Any,
        _FakeClient([_FakeStream([_text_delta(verdict[:10]), _text_delta(verdict[10:])], final)]),
    )
    agent = VerifierAgent(
        client=client,
        settings=Settings(),
        tools=_all_tools(),
        evidence_store=EvidenceStore(),
    )

    events = list(agent.verify())

    assert StreamEventKind.TEXT not in {event.kind for event in events}
    verify_results = [event for event in events if event.kind is StreamEventKind.VERIFY_RESULT]
    assert len(verify_results) == 1
    assert verify_results[0].text == verdict
    assert verify_results[0].verification_status is VerificationStatus.SOUND


def test_verify_classifies_needs_attention_verdict() -> None:
    verdict = "Needs attention\n\n- The dependency claim for the top pick is unsupported."
    final = _final_message([_text_delta(verdict)], "end_turn")
    client = cast(Any, _FakeClient([_FakeStream([_text_delta(verdict)], final)]))
    agent = VerifierAgent(
        client=client,
        settings=Settings(),
        tools=_all_tools(),
        evidence_store=EvidenceStore(),
    )

    events = list(agent.verify())

    verify_results = [event for event in events if event.kind is StreamEventKind.VERIFY_RESULT]
    assert len(verify_results) == 1
    assert verify_results[0].verification_status is VerificationStatus.NEEDS_ATTENTION
