from pydantic import BaseModel, Field


class EvidenceRecord(BaseModel):
    tool: str
    input: dict[str, object] = Field(default_factory=dict)
    data: object | None = None
    is_error: bool = False
