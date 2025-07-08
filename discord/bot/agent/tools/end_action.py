from agent.schema.base import (
    FunctionTool,
    ToolResponse,
    ParameterData,
    SuccessComponent,
    FailureComponent,
)


async def end_action_function(success: bool, reason: str | None = None) -> ToolResponse:
    return ToolResponse(
        content="Action ended successfully.",
        components=[SuccessComponent()]
        if success
        else [FailureComponent(error=reason or "Unknown error")],
        end_action=True,
    )


return_action = FunctionTool(
    name="return_action",
    description="Once the goal is achieved, end the action.",
    parameters={
        "success": ParameterData(
            type="boolean",
            description="Indicates whether the action was successful.",
            required=True,
        ),
        "reason": ParameterData(
            type="string",
            description="Optional reason for ending the action. Explanation of failure",
            required=False,
        ),
    },
    target_function=end_action_function,
)
