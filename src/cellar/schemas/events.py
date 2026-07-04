from enum import StrEnum

from pydantic import BaseModel


class StreamEventKind(StrEnum):
    TEXT = "text"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    DONE = "done"
    ERROR = "error"


class StreamEvent(BaseModel):
    kind: StreamEventKind
    text: str | None = None
    tool_name: str | None = None
    tool_input: dict[str, object] | None = None
    content: str | None = None
    is_error: bool = False
