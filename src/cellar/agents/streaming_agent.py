import json
from collections.abc import Iterator

from anthropic import NOT_GIVEN
from anthropic.types import Message, MessageParam

from cellar.config import Settings
from cellar.schemas.events import StreamEvent, StreamEventKind
from cellar.services.evidence_store import EvidenceStore, bind_store
from cellar.services.llm import LlmClient
from cellar.tools.base import Tool, ToolResult


def _parse_json(content: str) -> object | None:
    try:
        return json.loads(content)
    except (ValueError, TypeError):
        return content


class StreamingAgent:
    def __init__(
        self,
        client: LlmClient,
        settings: Settings,
        tools: list[Tool],
        system: str | None = None,
    ) -> None:
        self._client = client
        self._settings = settings
        self._tools_by_name = {tool.name: tool for tool in tools}
        self._system = system or NOT_GIVEN
        self._transcript: list[MessageParam] = []
        self._evidence = EvidenceStore()
        for tool in tools:
            if hasattr(tool, "evidence_store"):
                tool.evidence_store = self._evidence

    def send(self, user_message: str) -> Iterator[StreamEvent]:
        bind_store(self._evidence)
        self._transcript.append({"role": "user", "content": user_message})
        yield from self._run_until_end_turn()

    def _run_until_end_turn(self) -> Iterator[StreamEvent]:
        while True:
            with self._client.messages.stream(
                model=self._settings.model_name,
                max_tokens=self._settings.max_output_tokens,
                system=self._system,
                tools=[tool.to_api_schema() for tool in self._tools_by_name.values()],
                messages=self._transcript,
            ) as stream:
                for event in stream:
                    if event.type == "content_block_delta" and event.delta.type == "text_delta":
                        yield StreamEvent(kind=StreamEventKind.TEXT, text=event.delta.text)
                    elif event.type == "content_block_start" and event.content_block.type == "tool_use":
                        yield StreamEvent(
                            kind=StreamEventKind.TOOL_USE, tool_name=event.content_block.name
                        )
                response = stream.get_final_message()

            self._transcript.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                yield StreamEvent(kind=StreamEventKind.DONE)
                return
            yield from self._run_requested_tools(response)

    def _run_requested_tools(self, response: Message) -> Iterator[StreamEvent]:
        tool_results: list[dict[str, object]] = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            arguments = dict(block.input)
            tool = self._tools_by_name.get(block.name)
            outcome = (
                tool.run(arguments)
                if tool is not None
                else ToolResult(content=f"Unknown tool: {block.name}", is_error=True)
            )
            self._evidence.record(
                block.name, arguments, _parse_json(outcome.content), outcome.is_error
            )
            yield StreamEvent(
                kind=StreamEventKind.TOOL_RESULT,
                tool_name=block.name,
                tool_input=arguments,
                content=outcome.content,
                is_error=outcome.is_error,
            )
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": outcome.content,
                    "is_error": outcome.is_error,
                }
            )
        self._transcript.append({"role": "user", "content": tool_results})
