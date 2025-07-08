from __future__ import annotations
import asyncio
import logfire
import json
from collections.abc import AsyncGenerator

from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)
from openai.types.chat.chat_completion_message_tool_call_param import (
    ChatCompletionMessageToolCallParam,
    Function as ChatCompletionMessageToolCallFunctionParam,
)
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_system_message_param import (
    ChatCompletionSystemMessageParam,
)
from openai.types.chat.chat_completion_assistant_message_param import (
    ChatCompletionAssistantMessageParam,
)
from openai.types.chat.chat_completion_tool_message_param import (
    ChatCompletionToolMessageParam,
)

from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.chat_model import ChatModel
from openai import AsyncClient

from agent.schema.base import FunctionTool, ToolResponse, ComponentEvent, MessageEvent


DEFAULT_OPENAI_MODEL: ChatModel = "gpt-4o-mini-2024-07-18"


class OpenAIAgent:
    def __init__(
        self,
        api_key: str,
        tools: list[FunctionTool] | None = None,
        system_prompt: str | None = None,
        model: ChatModel = DEFAULT_OPENAI_MODEL,
    ):
        self.client = AsyncClient(api_key=api_key)
        self.system_prompt = (
            system_prompt
            or "You are a helpful assistant that can execute tools to assist the user."
        )
        self.tools: list[FunctionTool] = tools if tools is not None else []
        self.model: ChatModel = model
        self.max_loops = 5  # Maximum number of loops to prevent infinite loops

    def openai_tools(self) -> list[ChatCompletionToolParam]:
        return [tool.to_openai_function() for tool in (self.tools or [])]

    async def get_system_prompt(self) -> str | None:
        if isinstance(self.system_prompt, str):
            return self.system_prompt
        return None

    async def execute_tool(
        self,
        tool_call: ChatCompletionMessageToolCall,
    ) -> ToolResponse:
        function_name = None
        try:
            function_name = tool_call.function.name
            function_arguments_as_string = tool_call.function.arguments
            function_args = json.loads(function_arguments_as_string)

            with logfire.span(
                f"Executing tool {function_name}",
                tool_name=function_name,
                tool_args=function_args,
            ):
                tool = next(
                    (tool for tool in self.tools if tool.name == function_name),
                    None,
                )

                logfire.info(
                    f"Calling tool: {function_name}",
                    tool_name=function_name,
                    tool_args=function_args,
                    found=tool is not None,
                )
                if tool is None:
                    raise ValueError(f"Tool {function_name} not found.")

                try:
                    tool_response = await tool.target_function(**function_args)
                except Exception as e:
                    logfire.exception(f"Error executing tool {function_name}: {e}")
                    tool_response = ToolResponse(
                        content=f"Error executing tool {function_name}",
                    )

                logfire.info(
                    f"Tool response: {function_name}",
                    tool_name=function_name,
                    tool_response=tool_response.model_dump(),
                )

                return tool_response

        except json.JSONDecodeError as e:
            logfire.exception(
                f"Error decoding JSON arguments for tool {function_name}: {e}"
            )
        except Exception as e:
            logfire.exception(f"Error executing tool {tool_call}: {e}")
        return ToolResponse(
            content=f"Error executing tool {tool_call.function.name}:",
        )

    @logfire.instrument("openai-chat-complete", record_return=True)
    async def chat_complete(
        self,
        messages: list[ChatCompletionMessageParam],
        model: ChatModel = DEFAULT_OPENAI_MODEL,
        tools: list[ChatCompletionToolParam] | None = None,
        system_message: ChatCompletionSystemMessageParam | None = None,
    ) -> ChatCompletionMessage:
        if tools:
            response = await self.client.chat.completions.create(
                messages=([system_message] if system_message else []) + messages,
                model=model,
                tools=tools,
            )
        else:
            response = await self.client.chat.completions.create(
                messages=([system_message] if system_message else []) + messages,
                model=model,
            )
        return response.choices[0].message

    @logfire.instrument("openai-process-request: {input=}", record_return=True)
    async def process_input(
        self, input: str
    ) -> AsyncGenerator[MessageEvent | ComponentEvent]:
        history: list[ChatCompletionMessageParam] = []
        history.append(ChatCompletionUserMessageParam(role="user", content=input))
        loop_count = 0
        while loop_count < self.max_loops:
            loop_count += 1

            system_message = ChatCompletionSystemMessageParam(
                content=self.system_prompt,
                role="system",
            )

            response = await self.chat_complete(
                system_message=system_message,
                messages=history,
                model=self.model,
                tools=self.openai_tools() if loop_count < self.max_loops else None,
            )

            content = response.content
            tool_calls = response.tool_calls

            if not tool_calls:
                if content:
                    yield MessageEvent(
                        event="MessageEvent",
                        content=content,
                    )
                return

            history.append(
                ChatCompletionAssistantMessageParam(
                    content=content,
                    tool_calls=[
                        ChatCompletionMessageToolCallParam(
                            id=tool_call.id,
                            function=ChatCompletionMessageToolCallFunctionParam(
                                name=tool_call.function.name,
                                arguments=tool_call.function.arguments,
                            ),
                            type="function",
                        )
                        for tool_call in tool_calls
                    ],
                    role="assistant",
                )
            )

            tool_call_tasks = [self.execute_tool(tool_call) for tool_call in tool_calls]
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
                tool_response_message = ChatCompletionToolMessageParam(
                    content=tool_response.content or "<no response>",
                    tool_call_id=tool_call.id,
                    role="tool",
                )
                history.append(tool_response_message)
                if tool_response.end_action:
                    end = True

            if end:
                return
