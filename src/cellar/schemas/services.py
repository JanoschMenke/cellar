from collections.abc import Callable

from anthropic import Anthropic, AnthropicBedrock

McpTool = Callable[..., dict[str, object]]
ReasoningFn = Callable[..., dict[str, str]]
LlmClient = Anthropic | AnthropicBedrock
