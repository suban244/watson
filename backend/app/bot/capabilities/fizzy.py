import asyncio
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.capabilities import Capability
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.tools import ToolDefinition

from schema.fizzy import FizzyBoard, FizzyCard, FizzyCardDetail, FizzyComment
from services import fizzy as fizzy_service

MAYBE = ("maybe", "maybe?", "triage", "inbox", "backlog")
NOT_NOW = ("not now", "not-now", "not_now", "later", "someday")
DONE = ("done", "closed", "close", "complete", "completed")

Lane = Literal["open", "maybe", "not_now", "done", "golden", "stalled", "all"]
LANE_FILTERS: dict[str, fizzy_service.CardLane | None] = {
    "open": None,
    "maybe": "maybe",
    "not_now": "not_now",
    "done": "closed",
    "golden": "golden",
    "stalled": "stalled",
    "all": "all",
}


class FizzyCapability(Capability):
    async def on_tool_execute_error(
        self,
        ctx: RunContext,
        *,
        call: ToolCallPart,
        tool_def: ToolDefinition,
        args: dict,
        error: Exception,
    ):
        if (
            isinstance(error, ValueError)
            and tool_def.name in self._function_toolset.tools
        ):
            raise ModelRetry(str(error)) from error
        raise error


fizzy = FizzyCapability(
    id="fizzy",
    description=(
        "Manage the user's Fizzy boards: create, find, move, assign, tag and "
        "comment on cards (tasks, todos, bugs, ideas)."
    ),
    defer_loading=True,
    instructions="""\
Fizzy domain:
- Fizzy is the user's kanban board app. Work is tracked as cards on boards.
- Every card is in exactly one lane: "Maybe?" (triage, where new cards land
  unless a column is given), one of the board's own columns, "Not Now"
  (postponed) or "Done" (closed).
- Cards are referred to by number, e.g. #42. Numbers are fine to show the
  user; other ids are for tool calls only. Boards, columns and people are
  passed to tools by name, as listed in the Fizzy reference below.
- "me" / "I" as an assignee means the user themself.
- A card is not a reminder. Something to track on a board ("add X to my
  board", "todo: X", "make a card for X") belongs here; a nudge at a specific
  time ("remind me at 6pm") is a reminder.

Fizzy workflows:
1. Add a card:
    - User: "add fix the router to homelab", "todo: renew passport",
      "card for the leaking tap, assign me".
    - Steps:
        1. Pick the board from the user's wording. If more than one board
           could fit and nothing points to one, ask which.
        2. Call `create_card`. Put extra detail the user gave into
           `description`, not the title.
        3. Reply in one line with the card number, board and lane, e.g.
           "#42 on Homelab › Maybe?".

2. Find or review cards:
    - User: "what's on my homelab board?", "what am I working on?", "any
      cards about the router?", "what did I finish this week?"
    - Steps: call `find_cards` (or `show_card` for one card's detail and
      comments). Reply with a short list grouped by lane: number, title,
      assignees if relevant.

3. Move a card:
    - User: "move #42 to doing", "#42 is done", "push the passport card to
      not now", "reopen #12".
    - Steps:
        1. If the user named the card by title, find its number with
           `find_cards` first.
        2. Call `move_card`. "Done"/"finished" means `to="done"`; "reopen"
           means back to "maybe" unless they named a column.
        3. You can only return success_marker as your response.

4. Change a card:
    - Assign or unassign: `assign_card`. Tag or untag: `tag_card`. Rename or
      edit the description: `update_card`. Comment: `comment_on_card`.
      Checklist: `add_steps`, then `check_step` to tick items off.
    - Find the card number first if needed, then return success_marker.
""",
)


@fizzy.instructions
async def fizzy_reference() -> str | None:
    try:
        boards, users, me = await asyncio.gather(
            fizzy_service.list_boards(with_columns=True),
            fizzy_service.list_users(),
            fizzy_service.my_user_id(),
        )
    except ValueError as exc:
        return (
            f"Fizzy reference unavailable — tell the user if they ask for Fizzy: {exc}"
        )

    board_lines = "\n".join(
        f"- {board.name}: {', '.join(c.name for c in board.columns) or '(no columns)'}"
        for board in boards
    )
    people = ", ".join(f"{u.name} (the user)" if u.id == me else u.name for u in users)
    return (
        "Fizzy boards, with their own columns in order (every board also has "
        f"Maybe?, Not Now and Done):\n{board_lines or '- (no boards yet)'}\n"
        f"Fizzy people: {people}"
    )


def _pick[T](name: str, options: dict[str, T], kind: str) -> T:
    """Match `name` to one option, case-insensitively, exact before partial."""
    wanted = name.strip().lower()
    exact = [v for k, v in options.items() if k.lower() == wanted]
    if len(exact) == 1:
        return exact[0]
    partial = [v for k, v in options.items() if wanted in k.lower()]
    if len(partial) == 1:
        return partial[0]
    names = ", ".join(options) or "(none)"
    if partial:
        raise ModelRetry(f"'{name}' matches more than one {kind}. Options: {names}.")
    raise ModelRetry(f"No {kind} called '{name}'. Options: {names}.")


async def _board(name: str | None) -> FizzyBoard:
    boards = await fizzy_service.list_boards(with_columns=True)
    if name is None:
        if len(boards) == 1:
            return boards[0]
        raise ModelRetry(
            f"Which board? Options: {', '.join(b.name for b in boards) or '(none)'}."
        )
    return _pick(name, {b.name: b for b in boards}, "board")


async def _user_id(name: str) -> str:
    if name.strip().lower() in ("me", "i", "myself", "the user"):
        return await fizzy_service.my_user_id()
    users = await fizzy_service.list_users()
    return _pick(name, {u.name: u for u in users}, "person").id


def _column_id(board: FizzyBoard, name: str) -> str:
    return _pick(name, {c.name: c for c in board.columns}, f"column on {board.name}").id


class CreateCardParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="Short card title.")
    board: str | None = Field(
        default=None,
        description="Board name. May be omitted only when there is a single board.",
    )
    description: str | None = Field(
        default=None, description="Extra detail the user gave. Omit if none."
    )
    column: str | None = Field(
        default=None,
        description=(
            "One of the board's own columns. Omit to land in Maybe? (triage), "
            "which is the default unless the user named a column."
        ),
    )
    assignees: list[str] | None = Field(
        default=None, description='People\'s names, or "me". Omit if none were named.'
    )
    tags: list[str] | None = Field(
        default=None, description="Tag names; new ones are created. Omit if none."
    )


@fizzy.tool_plain
async def create_card(params: CreateCardParams) -> FizzyCard:
    """Create a card on a board and return it."""
    board = await _board(params.board)
    column_id = None
    if params.column and params.column.strip().lower() not in MAYBE:
        column_id = _column_id(board, params.column)
    assignee_ids = [await _user_id(name) for name in params.assignees or []]

    return await fizzy_service.create_card(
        board_id=board.id,
        title=params.title,
        description=params.description,
        column_id=column_id,
        assignee_ids=assignee_ids,
        tag_names=params.tags,
    )


class FindCardsParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    board: str | None = Field(
        default=None, description="Board name. Omit for all boards."
    )
    query: str | None = Field(
        default=None, description="Words to search card titles and text for."
    )
    assignee: str | None = Field(
        default=None, description='Only cards assigned to this person, or "me".'
    )
    tag: str | None = Field(default=None, description="Only cards with this tag.")
    lane: Lane = Field(
        default="open",
        description=(
            "open = everything not Done or Not Now (the default); maybe = triage "
            "only; not_now; done = closed cards; golden = starred; stalled = "
            "untouched for a while; all = every lane."
        ),
    )
    limit: int = Field(default=30, description="Maximum number of cards to return.")


@fizzy.tool_plain
async def find_cards(params: FindCardsParams) -> list[FizzyCard]:
    """List or search cards, most recently active first. Each card has its `lane`."""
    board_ids = [(await _board(params.board)).id] if params.board else None
    assignee_ids = [await _user_id(params.assignee)] if params.assignee else None
    tag_ids = None
    if params.tag:
        tags = await fizzy_service.list_tags()
        tag_ids = [_pick(params.tag, {t.title: t for t in tags}, "tag").id]

    return await fizzy_service.list_cards(
        board_ids=board_ids,
        assignee_ids=assignee_ids,
        tag_ids=tag_ids,
        terms=params.query.split() if params.query else None,
        lane=LANE_FILTERS[params.lane],
        limit=params.limit,
    )


class CardNumberParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: int = Field(description="The card number, e.g. 42 for #42.")


@fizzy.tool_plain
async def show_card(params: CardNumberParams) -> FizzyCardDetail:
    """One card in full: description, checklist steps and recent comments."""
    return await fizzy_service.get_card_detail(params.number)


class MoveCardParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: int = Field(description="The card number.")
    to: str = Field(
        description=(
            'Where it goes: one of the board\'s own columns, or "maybe", '
            '"not now" or "done".'
        )
    )
    board: str | None = Field(
        default=None,
        description="Only when moving to a different board: that board's name.",
    )


@fizzy.tool_plain
async def move_card(params: MoveCardParams) -> FizzyCard:
    """Move a card to another lane (and optionally another board).

    Closed cards are reopened automatically when moved anywhere but Done.
    """
    card = await fizzy_service.get_card(params.number)
    target = params.to.strip().lower()

    if params.board:
        board = await _board(params.board)
        if card.board is None or board.id != card.board.id:
            column_id = None
            if target not in MAYBE + NOT_NOW + DONE:
                column_id = _column_id(board, params.to)
            await fizzy_service.move_card_to_board(card.number, board.id, column_id)
            card = await fizzy_service.get_card(card.number)
            if column_id or target in MAYBE:
                return card
    else:
        boards = await fizzy_service.list_boards(with_columns=True)
        board = next((b for b in boards if card.board and b.id == card.board.id), None)
        if board is None:
            raise ModelRetry(f"Could not find the board #{card.number} is on.")

    if target in DONE:
        if not card.closed:
            await fizzy_service.close_card(card.number)
    elif target in NOT_NOW:
        await fizzy_service.postpone_card(card.number)
    else:
        column_id = None if target in MAYBE else _column_id(board, params.to)
        if card.closed:
            await fizzy_service.reopen_card(card.number)
        if column_id:
            await fizzy_service.triage_card(card.number, column_id)
        else:
            await fizzy_service.untriage_card(card.number)

    return await fizzy_service.get_card(card.number)


class UpdateCardParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: int = Field(description="The card number.")
    title: str | None = Field(default=None, description="New title. Omit to keep.")
    description: str | None = Field(
        default=None,
        description="New description; replaces the old one. Omit to keep.",
    )


@fizzy.tool_plain
async def update_card(params: UpdateCardParams) -> FizzyCard:
    """Rename a card or replace its description."""
    if params.title is None and params.description is None:
        raise ModelRetry("Pass a new title, a new description, or both.")
    return await fizzy_service.update_card(
        params.number, title=params.title, description=params.description
    )


class AssignCardParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: int = Field(description="The card number.")
    person: str = Field(description='Their name, or "me".')
    assign: bool = Field(default=True, description="False to unassign them instead.")


@fizzy.tool_plain
async def assign_card(params: AssignCardParams) -> FizzyCard:
    """Assign someone to a card, or unassign them. Safe to repeat."""
    user_id = await _user_id(params.person)
    card = await fizzy_service.get_card(params.number)
    # The endpoint toggles, so only call it when the state needs to change.
    if any(a.id == user_id for a in card.assignees) != params.assign:
        await fizzy_service.toggle_assignment(card.number, user_id)
        card = await fizzy_service.get_card(card.number)
    return card


class TagCardParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: int = Field(description="The card number.")
    tag: str = Field(description="Tag name; created if it does not exist.")
    add: bool = Field(default=True, description="False to remove the tag instead.")


@fizzy.tool_plain
async def tag_card(params: TagCardParams) -> FizzyCard:
    """Add a tag to a card, or remove one. Safe to repeat."""
    card = await fizzy_service.get_card(params.number)
    wanted = params.tag.strip().lstrip("#").lower()
    has_tag = any(t.lstrip("#").lower() == wanted for t in card.tags)
    # The endpoint toggles, so only call it when the state needs to change.
    if has_tag != params.add:
        await fizzy_service.toggle_tag(card.number, params.tag.strip().lstrip("#"))
        card = await fizzy_service.get_card(card.number)
    return card


class CommentParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: int = Field(description="The card number.")
    body: str = Field(description="The comment text.")


@fizzy.tool_plain
async def comment_on_card(params: CommentParams) -> FizzyComment:
    """Add a comment to a card."""
    return await fizzy_service.add_comment(params.number, params.body)


class AddStepsParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: int = Field(description="The card number.")
    steps: list[str] = Field(description="Checklist items to add, in order.")


@fizzy.tool_plain
async def add_steps(params: AddStepsParams) -> FizzyCard:
    """Add checklist steps to a card."""
    for content in params.steps:
        await fizzy_service.add_step(params.number, content)
    return await fizzy_service.get_card(params.number)


class CheckStepParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: int = Field(description="The card number.")
    step: str = Field(description="The step's text, or enough of it to identify it.")
    completed: bool = Field(default=True, description="False to untick it.")


@fizzy.tool_plain
async def check_step(params: CheckStepParams) -> FizzyCard:
    """Tick off (or untick) one checklist step on a card."""
    card = await fizzy_service.get_card(params.number)
    step = _pick(
        params.step, {s.content: s for s in card.steps}, f"step on #{card.number}"
    )
    await fizzy_service.set_step_completed(
        card.number, step.id, completed=params.completed
    )
    return await fizzy_service.get_card(card.number)
