import uuid

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import ModelRetry
from pydantic_ai.capabilities import Capability

from db.session import async_session_maker
from schema.ledger import (
    LedgerEntryCreate,
    LedgerEntryRead,
    LedgerEntryResult,
    LedgerShare,
    PersonBalance,
    PersonLedger,
    SharedEntryRead,
    SharedExpenseRead,
)
from schema.person import PersonRead
from schema.transaction import ExpenseCategory, TransactionCreate, TransactionRead
from services import ledger as ledger_service
from services import people as people_service
from utils.timezone import parse_date

SPLIT_TOLERANCE = 0.01


class Share(BaseModel):
    """What one person owes you out of a bill you paid."""

    model_config = ConfigDict(extra="forbid")

    person: str = Field(description="Their nickname or full name.")
    amount: float = Field(description="Their share in NPR, positive.")


ledger = Capability(
    id="ledger",
    description=(
        "Track money lent to and owed by people, split shared expenses, and "
        "settle up."
    ),
    defer_loading=True,
    instructions=f"""\
Lending domain:
- The currency is NPR (Nepalese Rupee); assume amounts are in NPR.
- A balance is per person and all-time: everything lent, split and repaid,
  netted. Positive means they owe the user; negative means the user owes them.
- Lending is NOT spending. `lend_money` records a debt and no expense, so the
  monthly budget never sees it. Never follow a `lend_money` call with
  `add_expense` for the same money — that would double-count it as spending.
- Repayment is not income either. Use `settle_up`, never `add_income`.
- These tools return records, not sentences. Every write hands back the new
  balance, so there is no need to look it up again afterwards.
- People are referred to by nickname — "raship", "anju-cousin" — which is
  unique and is what you pass to tools. Full names are optional and may be
  shared. Never show raw entry ids to the user; they are for tool calls only.
- If the user's wording could mean more than one person in the people
  reference, ask which before recording anything — money on the wrong
  person's ledger is worse than one extra question. If they mean someone new
  whose nickname would clash with someone on file, ask what to call them.

Lending workflows:
1. Lend money:
    - Trigger: user gave someone money they expect back.
    - User: "gave 5000 to raship", "lent anju 2000 for her ticket".
    - Steps:
        1. Call `lend_money`. It creates the person if they are new.
        2. You can only return success_marker as your response.

2. Borrow money:
    - Trigger: user received money they owe back, or someone paid for them.
    - User: "borrowed 1000 from anju", "anju covered my ticket, 800".
    - Steps: call `borrow_money`, then return success_marker.

3. Split a bill the user paid:
    - Trigger: user paid for something shared.
    - User: "handbrew 900 split between me and anju", "dinner 1200, three of
      us, I paid".
    - Steps:
        1. Work out the shares yourself. "Split between me and anju" means two
           ways: the user's share is 450 and anju owes 450. "Three of us" means
           three ways. If the user names uneven shares, use those.
        2. Call `split_expense` with `total_amount` as the whole bill,
           `my_share` as the user's own portion, and `owed` as one entry per
           other person. The tool checks that they add up and refuses if not.
        3. Pick a `category` and any `tags` exactly as you would for a normal
           expense — the user's share is a real expense and is recorded as one.
        4. Reply with the split so the user can check it, in one line: the
           total, their own share and its category, and what each person
           owes, using the nicknames from the result — e.g. "Handbrew 900:
           450 yours (dining_out), anju owes 450."
    - If the user paid but none of the bill was theirs, that is a loan, not a
      split: use `lend_money` instead.

4. Settle up:
    - Trigger: a debt is repaid, in either direction.
    - User: "raship paid me back 3000", "paid anju the 450 I owed".
    - Steps:
        1. Call `settle_up` with a positive amount. It works out the direction
           from the current balance, so never pass a negative number.
        2. You can only return success_marker as your response.
    - The returned balance says where things stand. If it crossed past zero,
      the user has overpaid and now owes the other way — say so.

5. Who owes what:
    - Trigger: user asks about debts.
    - User: "who owes me money?", "how much does raship owe me?"
    - Steps: call `list_balances`, or `person_history` for one person's
      entries. Return the answer as text, never success_marker.

6. Corrections:
    - Trigger: user wants to fix or remove a ledger entry.
    - User: "that was 400 not 500", "raship never actually took that".
    - Steps:
        1. Find the entry with `person_history`.
        2. Call `delete_ledger_entry`, then re-record it correctly if it was a
           correction rather than a removal. There is no update tool.
        3. Return success_marker as your response.

Expense categories, for the `category` on a split (pick the closest fit; omit
if genuinely unclear, defaults to misc):
{ExpenseCategory.reference()}
""",
)


@ledger.instructions
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


def _parse_date_or_retry(date: str | None):
    parsed = parse_date(date)
    if parsed is None:
        raise ModelRetry(f"'{date}' is not a valid date. Use YYYY-MM-DD.")
    return parsed


async def _write_entry(
    person: str, amount: float, title: str | None, date: str | None, *, fallback: str
) -> LedgerEntryResult:
    date_obj = _parse_date_or_retry(date)

    async with async_session_maker() as session:
        resolved = await _resolve(session, person, create=True)
        entry = await ledger_service.add_entry(
            session,
            resolved.id,
            LedgerEntryCreate(
                amount=amount,
                title=title or fallback.format(name=resolved.nickname),
                date=date_obj,
            ),
        )
        return LedgerEntryResult(
            entry=LedgerEntryRead.model_validate(entry),
            person=resolved,
            balance=await ledger_service.person_balance(session, resolved.id),
        )


class LendMoney(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person: str = Field(
        description="Who received it — nickname or full name. Created if they are new."
    )
    amount: float = Field(description="How much, in NPR, positive.")
    title: str | None = Field(
        default=None,
        description=(
            'What it was for, e.g. "Ticket money". Omit if the user did not say.'
        ),
    )
    date: str | None = Field(
        default=None, description="YYYY-MM-DD. Omit if it was today."
    )


@ledger.tool_plain
async def lend_money(params: LendMoney) -> LedgerEntryResult:
    """Record money the user lent someone and expects back.

    Writes no expense: lending is not spending, so this stays out of the
    monthly budget. Do not also call `add_expense` for the same money.
    """
    return await _write_entry(
        params.person,
        abs(params.amount),
        params.title,
        params.date,
        fallback="Lent to {name}",
    )


class BorrowMoney(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person: str = Field(
        description="Who it is owed to — nickname or full name. Created if they are new."
    )
    amount: float = Field(description="How much, in NPR, positive.")
    title: str | None = Field(
        default=None, description="What it was for. Omit if the user did not say."
    )
    date: str | None = Field(
        default=None, description="YYYY-MM-DD. Omit if it was today."
    )


@ledger.tool_plain
async def borrow_money(params: BorrowMoney) -> LedgerEntryResult:
    """Record money the user owes someone — they lent it, or covered something."""
    return await _write_entry(
        params.person,
        -abs(params.amount),
        params.title,
        params.date,
        fallback="Borrowed from {name}",
    )


class SplitExpense(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(description='What the bill was for, e.g. "Handbrew".')
    total_amount: float = Field(description="The whole bill in NPR, before splitting.")
    my_share: float = Field(
        description=(
            "The user's own portion. Must be more than zero — if none of the "
            "bill was theirs, use `lend_money` instead."
        )
    )
    owed: list[Share] = Field(
        description=(
            "One entry per other person, with their share. Together with "
            "`my_share` these must add up to `total_amount`."
        )
    )
    category: ExpenseCategory | None = Field(
        default=None,
        description=(
            "The category for the user's share. Pick the closest fit; omit if "
            "genuinely unclear (defaults to misc)."
        ),
    )
    date: str | None = Field(
        default=None, description="YYYY-MM-DD. Omit if it was today."
    )
    tags: list[str] | None = Field(
        default=None,
        description=(
            "Slugs of any active tags or pots this belongs to. Omit when none "
            "clearly applies; do not invent slugs."
        ),
    )


@ledger.tool_plain
async def split_expense(params: SplitExpense) -> SharedExpenseRead:
    """Record a bill the user paid and split with others.

    The user's own share is recorded as a normal expense; everyone else's
    share becomes a debt they owe, linked to it. Only `my_share` reaches the
    budget, which is what keeps the monthly totals honest.
    """
    if params.my_share <= 0:
        raise ModelRetry(
            "my_share must be more than zero. If none of this bill was the "
            "user's own, it is a loan — use lend_money instead."
        )
    if not params.owed:
        raise ModelRetry(
            "A split needs at least one other person; use add_expense instead."
        )

    claimed = params.my_share + sum(share.amount for share in params.owed)
    if abs(claimed - params.total_amount) > SPLIT_TOLERANCE:
        raise ModelRetry(
            f"The shares do not add up: {params.my_share:g} + "
            f"{' + '.join(f'{s.amount:g}' for s in params.owed)} = {claimed:g}, "
            f"but the bill is {params.total_amount:g}. Recheck the split."
        )

    date_obj = _parse_date_or_retry(params.date)

    async with async_session_maker() as session:
        nicknames: dict[uuid.UUID, str] = {}
        shares: list[LedgerShare] = []
        for share in params.owed:
            resolved = await _resolve(session, share.person, create=True)
            nicknames[resolved.id] = resolved.nickname
            shares.append(LedgerShare(person_id=resolved.id, amount=abs(share.amount)))

        expense = TransactionCreate(
            amount=params.my_share,
            date=date_obj,
            title=params.title,
            category=params.category or ExpenseCategory.MISC,
            is_expense=True,
            tags=params.tags or [],
        )

        try:
            transaction, entries = await ledger_service.record_shared_expense(
                session, expense, shares
            )
        except ValueError as exc:
            raise ModelRetry(str(exc)) from exc

        return SharedExpenseRead(
            transaction=TransactionRead.model_validate(transaction),
            entries=[
                SharedEntryRead(
                    **LedgerEntryRead.model_validate(entry).model_dump(),
                    nickname=nicknames[entry.person_id],
                )
                for entry in entries
            ],
        )


class SettleUp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person: str = Field(description="Who settled up — nickname or full name.")
    amount: float = Field(description="How much changed hands, in NPR, positive.")
    date: str | None = Field(
        default=None, description="YYYY-MM-DD. Omit if it was today."
    )


@ledger.tool_plain
async def settle_up(params: SettleUp) -> LedgerEntryResult:
    """Record a repayment, in whichever direction the debt runs.

    Pass a positive amount; the direction is worked out from the current
    balance. This writes no transaction — a repayment is not income.

    The returned `balance` is where things stand afterwards. Overpayment is not
    clamped: settling more than was owed pushes the balance past zero and the
    debt now runs the other way.
    """
    date_obj = _parse_date_or_retry(params.date)

    async with async_session_maker() as session:
        resolved = await _resolve(session, params.person)
        try:
            entry = await ledger_service.settle(
                session,
                resolved.id,
                params.amount,
                title=f"Settled with {resolved.nickname}",
                date=date_obj,
            )
        except ValueError as exc:
            raise ModelRetry(str(exc)) from exc

        return LedgerEntryResult(
            entry=LedgerEntryRead.model_validate(entry),
            person=resolved,
            balance=await ledger_service.person_balance(session, resolved.id),
        )


@ledger.tool_plain
async def list_balances() -> list[PersonBalance]:
    """List everyone and where the user stands with them.

    Includes people who are settled up, at a balance of zero — filter them out
    yourself if the user only asked who owes what.
    """
    async with async_session_maker() as session:
        return await ledger_service.balances(session)


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
        return PersonLedger(
            **resolved.model_dump(),
            balance=await ledger_service.person_balance(session, resolved.id),
            entries=[LedgerEntryRead.model_validate(entry) for entry in entries],
        )


class DeleteLedgerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_id: str = Field(description="The id of the entry, from `person_history`.")


@ledger.tool_plain
async def delete_ledger_entry(params: DeleteLedgerEntry) -> LedgerEntryRead:
    """Remove a ledger entry, returning what was removed.

    There is no update tool — to correct an entry, delete it and record it
    again from what comes back here.
    """
    try:
        parsed_id = uuid.UUID(params.entry_id)
    except ValueError as exc:
        raise ModelRetry(f"'{params.entry_id}' is not a valid entry id.") from exc

    async with async_session_maker() as session:
        entry = await ledger_service.get_entry(session, parsed_id)
        if entry is None:
            raise ModelRetry("No ledger entry with that id.")

        removed = LedgerEntryRead.model_validate(entry)
        await ledger_service.delete_entry(session, parsed_id)
        return removed
