from abc import ABC, abstractmethod

from pydantic import BaseModel, ValidationError

from cellar.schemas.tool_names import ToolName


class ToolResult(BaseModel):
    content: str
    is_error: bool = False


class Tool[InputT: BaseModel](ABC):
    name: ToolName
    description: str
    input_model: type[InputT]
    include_in_agent: bool = True

    @abstractmethod
    def run(self, arguments: InputT) -> ToolResult: ...

    def to_api_schema(self) -> dict[str, object]:
        schema = self.input_model.model_json_schema()
        return {"name": str(self.name), "description": self.description, "input_schema": schema}

    def dispatch(self, raw_arguments: dict[str, object]) -> ToolResult:
        try:
            arguments = self.input_model.model_validate(raw_arguments)
        except ValidationError as error:
            return ToolResult(content=f"Invalid arguments for {self.name}: {error}", is_error=True)
        return self.run(arguments)
