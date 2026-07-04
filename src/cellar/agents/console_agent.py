from anthropic import NOT_GIVEN
from anthropic.types import Message, MessageParam

from cellar.config import Settings
from cellar.services.llm import LlmClient
from cellar.tools.base import Tool


class ConsoleAgent:
    def __init__(
        self,
        client: LlmClient,
        settings: Settings,
        tools: list[Tool],
        server_tools: list[dict[str, object]] | None = None,
        system: str | None = None,
        verbose: bool = False,
    ) -> None:
        self._client = client
        self._settings = settings
        self._tools_by_name = {tool.name: tool for tool in tools}
        self._server_tools = server_tools or []
        self._system = system or NOT_GIVEN
        self._verbose = verbose
        self._transcript: list[MessageParam] = []

    def send(self, user_message: str) -> str:
        self._transcript.append({"role": "user", "content": user_message})
        return self._run_until_end_turn()

    def _run_until_end_turn(self) -> str:
        tools = [
            *self._server_tools,
            *(tool.to_api_schema() for tool in self._tools_by_name.values()),
        ]
        while True:
            response = self._client.messages.create(
                model=self._settings.model_name,
                max_tokens=self._settings.max_output_tokens,
                thinking={"type": "adaptive"},
                system=self._system,
                tools=tools,
                messages=self._transcript,
            )
            self._transcript.append({"role": "assistant", "content": response.content})
            self._log_server_tool_use(response)
            if response.stop_reason == "pause_turn":
                # A server-side tool (e.g. web_search) hit its internal iteration
                # cap. Resend as-is — no extra message — and the API resumes.
                continue
            if response.stop_reason != "tool_use":
                return _joined_text(response)
            self._transcript.append(
                {"role": "user", "content": self._execute_requested_tools(response)}
            )

    def _execute_requested_tools(self, response: Message) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            arguments = dict(block.input)
            tool = self._tools_by_name.get(block.name)
            if tool is None:
                self._log_tool(block.name, arguments, f"Unknown tool: {block.name}", is_error=True)
                results.append(_tool_result(block.id, f"Unknown tool: {block.name}", is_error=True))
                continue
            outcome = tool.run(arguments)
            self._log_tool(block.name, arguments, outcome.content, is_error=outcome.is_error)
            results.append(_tool_result(block.id, outcome.content, is_error=outcome.is_error))
        return results

    def _log_tool(
        self, name: str, arguments: dict[str, object], content: str, is_error: bool
    ) -> None:
        if not self._verbose:
            return
        marker = "✗" if is_error else "→"
        preview = content.replace("\n", " ")[:200]
        print(f"  {marker} tool {name}({arguments})")
        print(f"    ↳ {preview}")

    def _log_server_tool_use(self, response: Message) -> None:
        if not self._verbose:
            return
        for block in response.content:
            if block.type == "server_tool_use":
                print(f"  → server tool {block.name}({dict(block.input)})")


def _tool_result(tool_use_id: str, content: str, is_error: bool) -> dict[str, object]:
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content,
        "is_error": is_error,
    }


def _joined_text(response: Message) -> str:
    return "\n".join(block.text for block in response.content if block.type == "text").strip()
