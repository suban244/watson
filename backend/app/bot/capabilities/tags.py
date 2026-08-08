import uuid

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.capabilities import Capability

from db.models import Tag, TagStatus
from db.session import async_session_maker
from schema.tag import TagCreate
from services import tags as tag_service
from services import transactions as transaction_service


class ToolArgs(BaseModel):
    """Base for tool argument models.

    pydantic-ai flattens a single model-like argument, so these fields become the
    tool's own parameters; `extra="forbid"` keeps `additionalProperties: false`
    on the generated schema. Each model's docstring becomes the tool description.
    """

    model_config = ConfigDict(extra="forbid")


def format_tag(tag: Tag) -> str:
    kind = "pot" if tag.is_pot else "tag"
    limit = f" | limit {tag.limit_amount:g} NPR" if tag.limit_amount else ""
    excluded = " | excluded from monthly budget" if tag.exclude_from_monthly else ""
    description = f" — {tag.description}" if tag.description else ""
    return f"- {tag.slug} ({kind}){limit}{excluded}: {tag.name}{description}"


tags = Capability(
    id="tags",
    description="Create and manage tags and pots, and tag existing transactions.",
    defer_loading=True,
    instructions="""\
Tags and pots domain:
- A tag labels transactions. A "pot" is a tag that also tracks spending toward
  a theme, optionally against a limit — e.g. a trip, an event, or an ongoing
  commitment like college.
- Tags are referred to by slug (e.g. `fifa-final-2026`). Slugs are generated
  from the name and never change. Unlike record ids, slugs are fine to show the
  user, since they are how tagging gets discussed.
- Pots have no start or end date. They are opened and archived by hand, and
  their spending is counted purely from the transactions tagged into them.

Tag workflows:
1. Create a pot:
    - Trigger: user wants to track spending on a theme ("track what I spend on
      the fifa final", "make a college budget").
    - Steps:
        1. Call `create_pot` with a name, a `description` saying when a
           transaction belongs to it, and a `limit_amount` if the user gave a
           budget. Omit the limit when they only want tracking.
        2. You can only return success_marker as your response.
    - The description matters: it is what you will later use to decide whether
      a new expense belongs to this pot. Write it as a rule, not a restatement
      of the name. If the user's intent is too vague to write one, ask ONE
      short clarifying question.

2. Create a plain tag:
    - Trigger: user wants to label transactions without tracking a total
      ("tag things as work-reimbursable").
    - Steps: call `create_tag`, then return success_marker.

3. List tags and pots:
    - Trigger: user asks what tags or pots exist.
    - Steps: call `list_tags` and return a readable summary.

4. Tag or untag an existing transaction:
    - Trigger: user wants an already-recorded expense counted toward a pot
      ("put that dinner in the fifa pot", "that wasn't a college expense").
    - Steps:
        1. Find the transaction id — from conversation context if it is there,
           otherwise via `search_expenses` or `list_recent_transactions`.
        2. Call `tag_transaction` or `untag_transaction`.
        3. You can only return success_marker as your response.
    - Prefer tagging when the expense is first recorded, using the `tags`
      argument on `add_expense`. This workflow is for corrections and for
      expenses that predate the pot.

5. Archive a pot or tag:
    - Trigger: the trip is over, or the user is done with a label.
    - Steps: call `archive_tag`, then return success_marker.
    - Archiving keeps the tag on transactions that already carry it; it just
      stops being offered for new ones. Never describe this as deleting.

6. Change a pot's limit:
    - Trigger: user revises the budget for a pot.
    - Steps: call `set_pot_limit`, then return success_marker.
""",
)


class CreatePot(ToolArgs):
    """Create a pot: a tag that tracks spending toward a theme, optionally
    against a limit."""

    name: str = Field(description='Display name, e.g. "Fifa Final 2026".')
    description: str = Field(
        description=(
            "When a transaction belongs to this pot, phrased as a rule you can "
            'apply later (e.g. "Anything spent travelling to or at the final"). '
            "This is shown to you when deciding how to tag new expenses."
        )
    )
    limit_amount: float | None = Field(
        default=None,
        description=(
            "Budget for the pot in NPR. Omit when the user only wants to track "
            "the total without a cap."
        ),
    )
    exclude_from_monthly: bool = Field(
        default=False,
        description=(
            "Set when this pot's spending is a one-off that would distort the "
            "monthly budget (a trip, an event). Leave false for ongoing "
            "commitments like college, which are part of normal spending."
        ),
    )


@tags.tool_plain
async def create_pot(params: CreatePot) -> str:
    async with async_session_maker() as session:
        try:
            tag = await tag_service.create_tag(
                session,
                TagCreate(
                    name=params.name,
                    description=params.description,
                    is_pot=True,
                    limit_amount=params.limit_amount,
                    exclude_from_monthly=params.exclude_from_monthly,
                ),
            )
        except ValueError as exc:
            return str(exc)

    limit = (
        f" with a limit of {params.limit_amount:g} NPR" if params.limit_amount else ""
    )
    return f"Pot created: {tag.name} (slug {tag.slug}){limit}."


class CreateTag(ToolArgs):
    """Create a plain tag for labelling transactions, with no spend tracking."""

    name: str = Field(description='Display name, e.g. "Work Reimbursable".')
    description: str | None = Field(
        default=None,
        description=(
            "When to apply this tag. Shown to you when tagging new expenses, so "
            "write it as a rule."
        ),
    )


@tags.tool_plain
async def create_tag(params: CreateTag) -> str:
    async with async_session_maker() as session:
        try:
            tag = await tag_service.create_tag(
                session, TagCreate(name=params.name, description=params.description)
            )
        except ValueError as exc:
            return str(exc)

    return f"Tag created: {tag.name} (slug {tag.slug})."


@tags.tool_plain
async def list_tags() -> str:
    """List the active tags and pots, with their limits and descriptions."""
    async with async_session_maker() as session:
        results = await tag_service.list_tags(session, status=TagStatus.ACTIVE)

    if not results:
        return "No tags or pots have been created yet."

    response = "Active tags and pots:\n"
    for tag in results:
        response += format_tag(tag) + "\n"
    return response


class TagTransaction(ToolArgs):
    """Add tags to an existing transaction, keeping any it already has."""

    transaction_id: str = Field(
        description="The id of the transaction, from search or list results."
    )
    slugs: list[str] = Field(description='Tag slugs to add, e.g. ["fifa-final-2026"].')


@tags.tool_plain
async def tag_transaction(params: TagTransaction) -> str:
    try:
        parsed_id = uuid.UUID(params.transaction_id)
    except ValueError:
        return "Invalid transaction id."

    async with async_session_maker() as session:
        transaction = await transaction_service.get_transaction(session, parsed_id)
        if transaction is None:
            return "Transaction not found."

        merged = list(transaction.tags) + [
            slug for slug in params.slugs if slug not in transaction.tags
        ]
        try:
            updated = await transaction_service.update_transaction(
                session, parsed_id, {"tags": merged}
            )
        except ValueError as exc:
            return str(exc)

    if updated is None:
        return "Transaction not found."
    return f"Transaction now tagged: {', '.join(updated.tags) or 'none'}."


class UntagTransaction(ToolArgs):
    """Remove tags from a transaction, leaving its other tags in place."""

    transaction_id: str = Field(
        description="The id of the transaction, from search or list results."
    )
    slugs: list[str] = Field(description="Tag slugs to remove.")


@tags.tool_plain
async def untag_transaction(params: UntagTransaction) -> str:
    try:
        parsed_id = uuid.UUID(params.transaction_id)
    except ValueError:
        return "Invalid transaction id."

    removing = {tag_service.slugify(slug) for slug in params.slugs}

    async with async_session_maker() as session:
        transaction = await transaction_service.get_transaction(session, parsed_id)
        if transaction is None:
            return "Transaction not found."

        remaining = [slug for slug in transaction.tags if slug not in removing]
        if len(remaining) == len(transaction.tags):
            return "That transaction does not carry any of those tags."

        try:
            updated = await transaction_service.update_transaction(
                session, parsed_id, {"tags": remaining}
            )
        except ValueError as exc:
            return str(exc)

    if updated is None:
        return "Transaction not found."
    return f"Transaction now tagged: {', '.join(updated.tags) or 'none'}."


class SetPotLimit(ToolArgs):
    """Set or clear a pot's spending limit."""

    slug: str = Field(description='The pot\'s slug, e.g. "fifa-final-2026".')
    limit_amount: float | None = Field(
        default=None,
        description=(
            "The new limit in NPR. Omit to clear the limit so the pot just "
            "tracks its total."
        ),
    )


@tags.tool_plain
async def set_pot_limit(params: SetPotLimit) -> str:
    async with async_session_maker() as session:
        tag = await tag_service.get_tag_by_slug(
            session, tag_service.slugify(params.slug)
        )
        if tag is None:
            return f"No tag with slug '{params.slug}'."
        if not tag.is_pot:
            return f"'{tag.slug}' is a plain tag, not a pot, so it has no limit."

        try:
            await tag_service.update_tag(
                session, tag.id, {"limit_amount": params.limit_amount}
            )
        except ValueError as exc:
            return str(exc)

        name = tag.name

    if params.limit_amount is None:
        return f"Limit cleared on {name}; it now just tracks spending."
    return f"Limit for {name} set to {params.limit_amount:g} NPR."


class ArchiveTag(ToolArgs):
    """Retire a tag or pot. Transactions already carrying it keep it; it just
    stops being offered for new ones."""

    slug: str = Field(description='The slug to archive, e.g. "fifa-final-2026".')


@tags.tool_plain
async def archive_tag(params: ArchiveTag) -> str:
    async with async_session_maker() as session:
        tag = await tag_service.get_tag_by_slug(
            session, tag_service.slugify(params.slug)
        )
        if tag is None:
            return f"No tag with slug '{params.slug}'."
        if tag.status == TagStatus.ARCHIVED:
            return f"'{tag.slug}' is already archived."

        await tag_service.archive_tag(session, tag.id)
        name = tag.name

    return f"Archived {name}."
