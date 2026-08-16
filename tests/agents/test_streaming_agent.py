from types import SimpleNamespace

from cellar.agents.streaming_agent import StreamingAgent
from cellar.config import Settings
from cellar.schemas.events import StreamEventKind
from cellar.schemas.tool_inputs import CountCharactersInput
from cellar.schemas.tool_names import ToolName
from cellar.tools.base import Tool, ToolResult


class _EchoTool(Tool[CountCharactersInput]):
    name = ToolName.COUNT_CHARACTERS
    description = "echo"
    input_model = CountCharactersInput

    def run(self, arguments: CountCharactersInput) -> ToolResult:
        return ToolResult(content='{"ok": true}')


def _tool_use_block() -> SimpleNamespace:
    return SimpleNamespace(
        type="tool_use", name=ToolName.COUNT_CHARACTERS, id="tu_1", input={"text": "hi"}
    )


def _final_message(content: list[object], stop_reason: str) -> SimpleNamespace:
    return SimpleNamespace(content=content, stop_reason=stop_reason, container=None)


class _FakeStream:
    def __init__(self, events: list[object], final: SimpleNamespace) -> None:
        self._events = events
        self._final = final

    def __enter__(self) -> "_FakeStream":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def __iter__(self):
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


def test_agent_dispatches_tool_then_finishes() -> None:
    first = _FakeStream([], _final_message([_tool_use_block()], "tool_use"))
    second = _FakeStream(
        [], _final_message([SimpleNamespace(type="text", text="done")], "end_turn")
    )
    client = _FakeClient([first, second])
    agent = StreamingAgent(client, Settings(), tools=[_EchoTool()], system="sys")

    kinds = [event.kind for event in agent.send("hi")]

    assert StreamEventKind.TOOL_RESULT in kinds
    assert kinds[-1] == StreamEventKind.DONE
    recorded = agent.evidence_store
    assert recorded is not None
    assert recorded.latest(ToolName.COUNT_CHARACTERS) is not None
