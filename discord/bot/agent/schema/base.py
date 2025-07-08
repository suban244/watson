from pydantic import BaseModel
from mistralai.models.tool import Tool as MistralTool
from mistralai.models.function import Function as MistralFunction
from typing import Literal

# from mistralai.models.functiontool import FunctionTool as MistralFunctionTool
from openai.types.chat.chat_completion_tool_param import (
    ChatCompletionToolParam as OpenAIFunction,
)
from openai.types.shared_params.function_definition import (
    FunctionDefinition as OpenAIFunctionDefinition,
)
from typing import Any
from collections.abc import Callable, Coroutine


class SuccessComponent(BaseModel):
    pass


class FailureComponent(BaseModel):
    error: str


Component = SuccessComponent | FailureComponent


class ComponentEvent(BaseModel):
    event: Literal["ComponentEvent"]
    component: Component


class MessageEvent(BaseModel):
    event: Literal["MessageEvent"]
    content: str


Event = ComponentEvent | MessageEvent


class ToolResponse(BaseModel):
    content: str
    components: list[Component] | None = None
    end_action: bool = False


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

    def to_openai_function(self) -> OpenAIFunction:
        required = (
            list(k for k, v in (self.parameters or {}).items() if v.required)
            if self.parameters
            else []
        )
        function_definition = OpenAIFunctionDefinition(
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
        return OpenAIFunction(function=function_definition, type="function")
