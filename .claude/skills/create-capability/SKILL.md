---
name: create-capability
description: How to add or change a Watson bot capability and its tools (backend/app/bot/capabilities/). Use when creating a new capability, adding a tool to an existing one, or converting old-style tools.
---

# Creating a capability

A capability is a domain of tools the agent loads on demand. It lives in
`backend/app/bot/capabilities/<domain>.py` and only talks to the service layer.

## Layering

```
db/models.py → schema/<domain>.py → services/<domain>.py → bot/capabilities/<domain>.py
                                                         ↘ api/endpoints/<domain>.py
```

- Capabilities never build queries; they call `services.<domain>`.
- Services raise `ValueError` with a message meant to be shown as-is.
- Capabilities turn that into `ModelRetry`.

## The capability

```python
people = Capability(
    id="people",
    description="One line the agent uses to decide whether to load this.",
    defer_loading=True,
    instructions="""\
People domain:
- Facts and rules about the domain, one per bullet.

People workflows:
1. Remember something about a person:
    - Trigger: when this applies.
    - User: "example phrasing", "another".
    - Steps:
        1. Call `tool_name`.
        2. You can only return success_marker as your response.
""",
)
```

- Use a plain ✅ (`success_marker` only) for simple writes. When the model had to
  interpret or calculate something (a split, a date, a guess), have it reply
  with what it recorded so the user can check.
- Context that changes at runtime goes in an `@<cap>.instructions` hook that
  returns `str | None`. Return `None` when there's nothing to inject.

## Tools

One `<ToolName>Params` model per tool, passed as the only argument:

```python
class PersonHistoryParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person: str = Field(description="Their nickname or full name.")
    limit: int = Field(default=20, description="Maximum number of entries to return.")


@ledger.tool_plain
async def person_history(params: PersonHistoryParams) -> PersonLedger:
    """One person's ledger entries, newest first, with their balance.

    Use this to find an entry the user wants to correct or remove.
    """
    async with async_session_maker() as session:
        resolved = await _resolve(session, params.person)
        entries = await ledger_service.list_entries(
            session, person_id=resolved.id, limit=params.limit
        )
        return PersonLedger(...)
```

- **Params:** `extra="forbid"`, and a `Field(description=...)` on every field.
  pydantic-ai flattens a single model argument, so these fields become the
  tool's parameters. No docstring on the Params class.
- **Docstring:** what the tool does and when to use it. No `Args:` block — the
  field descriptions already cover it.
- **No arguments:** leave out the Params model (`async def list_balances() -> ...`).
- **Return schema objects, not strings.** CodeMode composes tool results in
  Python. Build `XRead.model_validate(orm_obj)` inside the session, before it closes.
- **Errors:** `raise ModelRetry(...)` with a message that names the valid
  options, so the model can fix itself. An empty result is `[]`, not an error.
- **Ids:** fine in tool results, never shown to the user. Where there's a
  human handle (a nickname, a slug), accept that instead of an id.

## Registering

1. Export it from `bot/capabilities/__init__.py` (keep `__all__` sorted).
2. Add it to `capabilities=[...]` in `bot/agent/watson.py`.
3. New tables: add the models to `SCHEMA_REFERENCE` in `bot/capabilities/database.py`,
   plus a bullet there for anything SQL could get wrong (e.g. signed amounts).
4. If another capability's instructions would otherwise grab this request
   (e.g. a loan recorded as an expense), add a routing line there.

## Comments

Keep them minimal. Tool docstrings, `Field` descriptions and `instructions` are
prompt, not comments — they stay, and are worth wording carefully.
