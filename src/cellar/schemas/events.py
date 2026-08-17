from enum import StrEnum

from pydantic import BaseModel

from cellar.schemas.verification import VerificationStatus


class StreamEventKind(StrEnum):
    TEXT = "text"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    SERVER_TOOL_RESULT = "server_tool_result"
    VERIFY_START = "verify_start"
    VERIFY_RESULT = "verify_result"
    DONE = "done"
    ERROR = "error"


class StreamEvent(BaseModel):
    kind: StreamEventKind
    text: str | None = None
    tool_name: str | None = None
    tool_input: dict[str, object] | None = None
    content: str | None = None
    is_error: bool = False
    verification_status: VerificationStatus | None = None
