import json
from collections.abc import Generator, Iterator
from typing import Any, cast

from anthropic import omit
from anthropic.types import Message, MessageParam, ToolResultBlockParam, ToolUnionParam

from cellar.config import Settings
from cellar.schemas.events import StreamEvent, StreamEventKind
from cellar.schemas.tool_names import VERIFIER_EXCLUDED_TOOLS, ToolName
from cellar.schemas.verification import classify_verification_status
from cellar.services.evidence_store import EvidenceStore, bind_store
from cellar.services.llm import LlmClient
from cellar.tools.base import Tool, ToolResult


def _parse_json(content: str) -> object | None:
    try:
        return cast(object, json.loads(content))
    except (ValueError, TypeError):
        return content


def _digest(store: EvidenceStore) -> str:
    counts: dict[str, int] = {}
    for record in store.records():
        counts[record.tool] = counts.get(record.tool, 0) + 1
    lines = ["Evidence already gathered (tool: number of calls):"]
    lines += [f"- {tool}: {n}" for tool, n in sorted(counts.items())] or ["- (none)"]

    latest = store.latest(ToolName.BUILD_RECOMMENDATIONS) or store.latest(ToolName.RECOMMEND_MODELS)
    if latest and isinstance(latest.data, dict):
        cards = latest.data.get("cards") or []
        compact = [
            {
                "model": c.get("model_name"),
                "recommended": c.get("recommended"),
                "reasons": [d.get("label") for d in (c.get("reasons") or [])],
                "watch_outs": [d.get("label") for d in (c.get("watch_outs") or [])],
            }
            for c in cards[:3]
        ]
        lines.append("\nRecommendation to verify (top cards):")
        lines.append(
            json.dumps({"verdict": latest.data.get("verdict"), "cards": compact}, indent=2)
        )
    else:
        lines.append("\nNo recommendation has been produced yet.")
    return "\n".join(lines)


class VerifierAgent:
    def __init__(
        self,
        client: LlmClient,
        settings: Settings,
        tools: list[Tool[Any]],
        evidence_store: EvidenceStore,
        system: str | None = None,
    ) -> None:
        self._client = client
        self._settings = settings
        self._tools_by_name: dict[str, Tool[Any]] = {
            tool.name: tool for tool in tools if tool.name not in VERIFIER_EXCLUDED_TOOLS
        }
        self._evidence = evidence_store
        self._system = system or omit

    def verify(self) -> Iterator[StreamEvent]:
        bind_store(self._evidence)
        for tool in self._tools_by_name.values():
            if hasattr(tool, "evidence_store"):
                tool.evidence_store = self._evidence
        transcript: list[MessageParam] = [
            {"role": "user", "content": _digest(self._evidence) + "\n\nVerify it now. Be fast."}
        ]
        tools = cast(
            "list[ToolUnionParam]",
            [tool.to_api_schema() for tool in self._tools_by_name.values()],
        )
        verdict_parts: list[str] = []

        for _ in range(self._settings.verifier_max_tool_rounds):
            response = yield from self._stream_turn(transcript, tools, verdict_parts)
            if response.stop_reason != "tool_use":
                yield self._verdict_event(verdict_parts)
                yield StreamEvent(kind=StreamEventKind.DONE)
                return
            yield from self._run_tools(response, transcript)

        transcript.append(
            {
                "role": "user",
                "content": "Tool budget spent. Give your final verdict now, no more tools.",
            }
        )
        yield from self._stream_turn(transcript, tools=None, verdict_parts=verdict_parts)
        yield self._verdict_event(verdict_parts)
        yield StreamEvent(kind=StreamEventKind.DONE)

    def _verdict_event(self, verdict_parts: list[str]) -> StreamEvent:
        verdict_markdown = "".join(verdict_parts)
        return StreamEvent(
            kind=StreamEventKind.VERIFY_RESULT,
            text=verdict_markdown,
            verification_status=classify_verification_status(verdict_markdown),
        )

    def _stream_turn(
        self,
        transcript: list[MessageParam],
        tools: list[ToolUnionParam] | None,
        verdict_parts: list[str],
    ) -> Generator[StreamEvent, None, Message]:
        with self._client.messages.stream(
            model=self._settings.model_name,
            max_tokens=self._settings.verifier_max_tokens,
            system=self._system,
            messages=transcript,
            tools=tools if tools else omit,
        ) as stream:
            for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    verdict_parts.append(event.delta.text)
                elif event.type == "content_block_start" and event.content_block.type == "tool_use":
                    yield StreamEvent(
                        kind=StreamEventKind.TOOL_USE, tool_name=event.content_block.name
                    )
            response = stream.get_final_message()
        transcript.append({"role": "assistant", "content": response.content})
        return response

    def _run_tools(
        self, response: Message, transcript: list[MessageParam]
    ) -> Iterator[StreamEvent]:
        tool_results: list[ToolResultBlockParam] = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            arguments = dict(block.input)
            tool = self._tools_by_name.get(block.name)
            outcome = (
                tool.dispatch(arguments)
                if tool is not None
                else ToolResult(
                    content=f"Tool not available to the verifier: {block.name}", is_error=True
                )
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
        transcript.append({"role": "user", "content": tool_results})
