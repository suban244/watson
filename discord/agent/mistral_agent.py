from agent.schema import FunctionTool, ToolResponse

from mistralai import Mistral
from mistralai.models.chatcompletionrequest import Messages
from mistralai.models.usermessage import UserMessage
from mistralai.models.assistantmessage import AssistantMessageContent
from mistralai.models.toolmessage import ToolMessage
from mistralai.models.assistantmessage import AssistantMessage
from mistralai.models.textchunk import TextChunk
from mistralai.models.completionargs import CompletionArgsTypedDict
from mistralai.models.tool import Tool as MistralTool
from mistralai.types.basemodel import OptionalNullable
from mistralai.models.toolcall import ToolCall
import logfire
from typing import Any
import json


class MistralAgent:
    def __init__(self, api_key: str, tools: list[FunctionTool] | None = None):
        self.client = Mistral(api_key=api_key)
        self.completion_args: CompletionArgsTypedDict = {
            "temperature": 0.7,
            "max_tokens": 2048,
            "top_p": 1,
        }
        self.tools: list[FunctionTool] = tools if tools is not None else []
        self.model = "open-mistral-nemo"

    def mistral_tools(self) -> list[MistralTool]:
        return [tool.to_mistral_tool() for tool in (self.tools or [])]

    @logfire.instrument("mistral-execute-tool: {tool_name=}", record_return=True)
    async def execute_tool(
        self, tool_name: str, arguments: dict[str, Any] | str
    ) -> ToolResponse:
        for tool in self.tools:
            if tool.name == tool_name:
                try:
                    parsed_arguments = (
                        arguments
                        if isinstance(arguments, dict)
                        else json.loads(arguments)
                    )
                    response = await tool.target_function(**parsed_arguments)
                    return response
                except Exception as e:
                    raise e
                    return ToolResponse(
                        content=f"Error executing tool {tool_name}: {str(e)}"
                    )

        return ToolResponse(content=f"Count not find tool with name: {tool_name}")

    @staticmethod
    def _mistral_extract_content(
        content: OptionalNullable[AssistantMessageContent],
    ) -> str | None:
        if not content:
            return None
        if isinstance(content, str):
            return content
        else:
            return "".join(
                chunk.text if isinstance(chunk, TextChunk) else str(chunk)
                for chunk in content
            )

    @staticmethod
    def _mistral_extract_tool_calls(
        tool_calls: OptionalNullable[list[ToolCall]],
    ) -> list[ToolCall]:
        if not tool_calls:
            return []
        return tool_calls

    @logfire.instrument("mistral-chat-complete", record_return=True)
    async def chat_complete(
        self,
        messages: list[Messages],
        model: str = "open-mistral-nemo",
        tools: list[MistralTool] | None = None,
    ) -> AssistantMessage:
        response = await self.client.chat.complete_async(
            messages=messages,
            model=model,
            tools=tools,
            **self.completion_args,
        )
        return response.choices[0].message

    @logfire.instrument("mistral-process-request: {input=}", record_return=True)
    async def process_input(self, input: str) -> str:
        history: list[Messages] = []
        history.append(
            UserMessage(
                content=input,
                role="user",
            )
        )
        try:
            tools = self.mistral_tools()
            model = self.model

            response = await self.chat_complete(
                messages=history,
                model=model,
                tools=tools,
            )

            content = self._mistral_extract_content(response.content)
            tool_calls = response.tool_calls

            if not tool_calls:
                return content or "<No Response>"

            print("Tool calls detected:")
            history.append(
                AssistantMessage(
                    content=content,
                    tool_calls=tool_calls,
                    role="assistant",
                )
            )
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_arguments: dict[str, Any] | str = tool_call.function.arguments

                tool_response = await self.execute_tool(tool_name, tool_arguments)

                if tool_response.content:
                    history.append(
                        ToolMessage(
                            content=tool_response.content,
                            tool_call_id=tool_call.id,
                            name=tool_name,
                            role="tool",
                        )
                    )

            response = await self.chat_complete(
                messages=history,
                model=model,
            )
            return self._mistral_extract_content(response.content) or "<No Response>"

        except Exception as e:
            print(f"Error: {str(e)}")
            return ""
