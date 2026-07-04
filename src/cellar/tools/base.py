from abc import ABC, abstractmethod

from pydantic import BaseModel


class ToolResult(BaseModel):
    content: str
    is_error: bool = False


class Tool(ABC):
    name: str
    description: str
    input_schema: dict[str, object]
    include_in_agent: bool = True

    @abstractmethod
    def run(self, arguments: dict[str, object]) -> ToolResult: ...

    def to_api_schema(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
