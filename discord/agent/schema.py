from pydantic import BaseModel
from mistralai.models.tool import Tool as MistralTool
from mistralai.models.function import Function as MistralFunction

# from mistralai.models.functiontool import FunctionTool as MistralFunctionTool
from typing import Any
from collections.abc import Callable, Coroutine


class ToolResponse(BaseModel):
    content: str


class ParameterData(BaseModel):
    type: str = "string"
    description: str | None = None
    required: bool = True


class FunctionTool(BaseModel):
    name: str
    description: str
    parameters: dict[str, ParameterData] | None = None
    strict_config: bool = False

    target_function: Callable[..., Coroutine[Any, Any, ToolResponse]]

    def to_mistral_tool(self) -> MistralTool:
        required = (
            list(k for k, v in (self.parameters or {}).items() if v.required)
            if self.parameters
            else []
        )
        tool = MistralFunction(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    k: v.model_dump(exclude_none=True, exclude={"required"})
                    for k, v in (self.parameters or {}).items()
                },
                "required": required,
            },
            strict=self.strict_config,
        )
        return MistralTool(function=tool, type="function")
