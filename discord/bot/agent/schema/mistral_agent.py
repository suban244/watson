from agent.schema.base import FunctionTool, ToolResponse, ComponentEvent, MessageEvent

from mistralai import Mistral
from mistralai.models.chatcompletionrequest import Messages
from mistralai.models.usermessage import UserMessage
from mistralai.models.systemmessage import SystemMessage
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
import asyncio
from collections.abc import AsyncGenerator

from enum import StrEnum


class MistralModel(StrEnum):
    SMALL = "mistral-small-latest"
    MEDIUM = "mistral-medium-2505"
    MINISTRAL_3B = "ministral-3b-latest"
    MINISTRAL_8B = "ministral-8b-latest"


class MistralAgent:
    def __init__(
        self,
        api_key: str,
        tools: list[FunctionTool] | None = None,
        system_prompt: str | None = None,
        model: MistralModel = MistralModel.SMALL,
    ):
        self.client = Mistral(api_key=api_key)
        self.system_prompt = (
            system_prompt
            or "You are a helpful assistant that can execute tools to assist the user."
        )
        self.completion_args: CompletionArgsTypedDict = {
            "temperature": 0.7,
            "max_tokens": 2048,
            "top_p": 1,
        }
        self.tools: list[FunctionTool] = tools if tools is not None else []
        self.model: MistralModel = model

        self.max_loops = 5  # Maximum number of loops to prevent infinite loops

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
        model: str = "mistral-small-latest",
        tools: list[MistralTool] | None = None,
        system_message: SystemMessage | None = None,
    ) -> AssistantMessage:
        response = await self.client.chat.complete_async(
            messages=([system_message] if system_message else []) + messages,
            model=model,
            tools=tools,
            **self.completion_args,
        )
        return response.choices[0].message

    async def tool_call_task(self, tool_call: ToolCall) -> ToolResponse:
        tool_name = tool_call.function.name
        tool_arguments: dict[str, Any] | str = tool_call.function.arguments

        tool_response = await self.execute_tool(tool_name, tool_arguments)
        return tool_response

    @logfire.instrument("mistral-process-request: {input=}", record_return=True)
    async def process_input(
        self, input: str
    ) -> AsyncGenerator[MessageEvent | ComponentEvent, None]:
        history: list[Messages] = []
        history.append(
            UserMessage(
                content=input,
                role="user",
            )
        )

        loop_count = 0
        while loop_count < self.max_loops:
            loop_count += 1

            system_message = SystemMessage(
                content=self.system_prompt,
                role="system",
            )

            response = await self.chat_complete(
                system_message=system_message,
                messages=history,
                model=self.model.value,
                tools=self.mistral_tools() if loop_count < self.max_loops else None,
            )

            content = self._mistral_extract_content(response.content)
            tool_calls = response.tool_calls

            if not tool_calls:
                if content:
                    yield MessageEvent(
                        event="MessageEvent",
                        content=content,
                    )
                return

            history.append(
                AssistantMessage(
                    content=content,
                    tool_calls=tool_calls,
                    role="assistant",
                )
            )

            tool_call_tasks = [
                self.tool_call_task(tool_call) for tool_call in tool_calls
            ]
            tool_call_responses = await asyncio.gather(
                *tool_call_tasks, return_exceptions=True
            )
            end = False
            for tool_call, tool_response in zip(tool_calls, tool_call_responses):
                if isinstance(tool_response, BaseException):
                    logfire.error(f"Error executing tool: {str(tool_response)}")
                    continue
                for component in tool_response.components or []:
                    yield ComponentEvent(
                        event="ComponentEvent",
                        component=component,
                    )
                tool_response_message = ToolMessage(
                    content=tool_response.content or "<no response>",
                    tool_call_id=tool_call.id,
                    name=tool_call.function.name,
                    role="tool",
                )
                history.append(tool_response_message)
                if tool_response.end_action:
                    end = True

            if end:
                return
