from pydantic_ai import ModelRetry
from pydantic_ai.capabilities import Capability

from db.session import async_session_maker
from schema.person import PersonCreate, PersonRead
from services import people as people_service

people = Capability(
    id="people",
    description="Look up and remember details about people — contacts, facts, notes.",
    defer_loading=True,
    instructions="""\
People domain:
- A person has a nickname, an optional full name, and whatever other details
  are worth keeping: an email, a phone number, how the user knows them.
- The nickname is how the user refers to them in chat — "anju", "raship",
  "anju-cousin". It is unique, and it is what you pass to tools. The full name
  is the formal one ("Anju Shrestha"), for emails and invoices; it is optional,
  and two people may share one.
- Other details live in a free-form bag under `meta`, so any key is allowed.
  Use plain lowercase keys like `email`, `phone`, `note`, and prefer an
  existing key over inventing a near-duplicate.
- These tools return records, not sentences. Read the fields you need and word
  the reply yourself.
- If the user's wording could mean more than one person in the reference below,
  ask which before acting — never guess. If they mean someone new whose
  nickname would clash with someone on file, ask what to call them instead.
- Money owed between the user and a person is NOT here — that is the `ledger`
  capability. This one only knows who someone is.

People workflows:
1. Remember something about a person:
    - Trigger: user states a fact about someone ("anju's email is a@b.com",
      "raship pays by esewa").
    - Steps:
        1. Call `save_person_detail`. It creates the person if they are new,
           so there is no need to add them first.
        2. You can only return success_marker as your response.

2. Set a full name, or change a nickname:
    - Trigger: "raship's full name is Raship Karki", "call her anju-di from
      now on".
    - Steps: call `update_person`, then return success_marker.

3. Recall what is known about a person:
    - Trigger: user asks about someone ("what's anju's email?", "what do I
      know about raship?").
    - Steps: call `person_details` and answer from its `full_name` and `meta`.
      If what they asked for is not there, say so rather than guessing.

4. List people:
    - Trigger: user asks who is on file.
    - Steps: call `list_people` and summarise what comes back.

5. Add someone with no details yet:
    - Trigger: user wants a person on file for its own sake.
    - Steps: call `add_person`, with the full name if the user gave one, then
      return success_marker.
    - Rarely needed on its own — recording a detail or a loan creates the
      person as a side effect.
""",
)


@people.instructions
async def known_people_reference() -> str | None:
    async with async_session_maker() as session:
        reference = await people_service.person_reference(session)
    if reference is None:
        return None
    return (
        "People already on file, as `nickname: full name` (match the user's "
        "wording to one of these rather than creating a new person for a "
        "spelling variant; if more than one could match, ask which):\n"
        f"{reference}"
    )


async def _resolve(session, person: str, *, create: bool = False) -> PersonRead:
    try:
        resolved = await people_service.resolve_person(session, person, create=create)
    except ValueError as exc:
        raise ModelRetry(str(exc)) from exc

    if resolved is None:
        raise ModelRetry(
            f"Nobody on file matching '{person}'. Check the people reference in "
            "your instructions for who the user meant."
        )
    return PersonRead.model_validate(resolved)


@people.tool_plain
async def add_person(nickname: str, full_name: str | None = None) -> PersonRead:
    """Add a person to the database with no details yet.

    Args:
        nickname: What the user calls them, e.g. "max". Must not clash with
            anyone already on file.
        full_name: Their formal name, e.g. "Max Thapa". Omit if not given.
    """
    async with async_session_maker() as session:
        try:
            person = await people_service.create_person(
                session, PersonCreate(nickname=nickname, full_name=full_name)
            )
        except ValueError as exc:
            raise ModelRetry(str(exc)) from exc
        return PersonRead.model_validate(person)


@people.tool_plain
async def update_person(
    person: str,
    nickname: str | None = None,
    full_name: str | None = None,
) -> PersonRead:
    """Set someone's full name, or change their nickname. Only the fields
    given are changed.

    Args:
        person: Their current nickname, or full name.
        nickname: A new nickname. Must not clash with anyone already on file.
        full_name: Their formal name, e.g. "Raship Karki".
    """
    updates = {
        key: value
        for key, value in {"nickname": nickname, "full_name": full_name}.items()
        if value is not None
    }
    if not updates:
        raise ModelRetry("Pass a new nickname, a full name, or both.")

    async with async_session_maker() as session:
        resolved = await _resolve(session, person)
        try:
            updated = await people_service.update_person(session, resolved.id, updates)
        except ValueError as exc:
            raise ModelRetry(str(exc)) from exc
        if updated is None:
            raise ModelRetry(f"Nobody on file matching '{person}'.")
        return PersonRead.model_validate(updated)


@people.tool_plain
async def save_person_detail(person: str, key: str, value: str) -> PersonRead:
    """Save one detail about a person, leaving their other details alone.
    Creates the person if they are not on file yet.

    For their full name use `update_person` instead — it is not a detail.

    Args:
        person: Their nickname, or full name.
        key: What kind of detail it is — `email`, `phone`, `note`. Lowercase,
            and reuse an existing key rather than inventing a near-duplicate.
        value: The detail itself.
    """
    async with async_session_maker() as session:
        resolved = await _resolve(session, person, create=True)
        updated = await people_service.set_detail(session, resolved.id, key, value)
        if updated is None:
            raise ModelRetry(f"Nobody on file matching '{person}'.")
        return PersonRead.model_validate(updated)


@people.tool_plain
async def list_people() -> list[PersonRead]:
    """List everyone on file, with the details known about them.

    Returns an empty list when nobody is on file yet.
    """
    async with async_session_maker() as session:
        results = await people_service.list_people(session)
        return [PersonRead.model_validate(person) for person in results]


@people.tool_plain
async def person_details(person: str) -> PersonRead:
    """Look up one person and everything known about them.

    Args:
        person: Their nickname, or full name.
    """
    async with async_session_maker() as session:
        return await _resolve(session, person)


@people.tool_plain
async def forget_person(person: str) -> PersonRead:
    """Remove a person from the database entirely, returning who was removed.

    Refused while they still have ledger entries, since deleting them would
    take that history with it — settle up or delete the entries first.

    Args:
        person: Their nickname, or full name.
    """
    async with async_session_maker() as session:
        resolved = await _resolve(session, person)
        try:
            await people_service.delete_person(session, resolved.id)
        except ValueError as exc:
            raise ModelRetry(str(exc)) from exc
        return resolved
