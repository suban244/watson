"""Shared tag queries used by both the API endpoints and the bot agent.

The pot-only fields (`limit_amount`, `exclude_from_monthly`) are enforced here
rather than by a DB constraint.

Validation failures raise `ValueError` with a message meant to be shown as-is —
the API turns it into a 400, the agent returns it as tool output — so the text
names the valid options.
"""

import re
import uuid
from collections.abc import Collection, Iterable, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Tag, TagStatus, Transaction
from schema.tag import TagCreate

MAX_TAGS_PER_TRANSACTION = 5

SLUG_MAX_LENGTH = 50

_NON_SLUG_CHARS = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """`"Fifa Final 2026"` -> `"fifa-final-2026"`."""
    return _NON_SLUG_CHARS.sub("-", value.strip().lower()).strip("-")[:SLUG_MAX_LENGTH]


def _reject_pot_fields_on_plain_tag(
    *, is_pot: bool, limit_amount: float | None, exclude_from_monthly: bool
) -> None:
    if is_pot:
        return
    if limit_amount is not None:
        raise ValueError("limit_amount is only valid on a pot; set is_pot first.")
    if exclude_from_monthly:
        raise ValueError(
            "exclude_from_monthly is only valid on a pot; set is_pot first."
        )


async def create_tag(session: AsyncSession, data: TagCreate) -> Tag:
    slug = slugify(data.slug or data.name)
    if not slug:
        raise ValueError("Could not derive a slug from that name.")

    _reject_pot_fields_on_plain_tag(
        is_pot=data.is_pot,
        limit_amount=data.limit_amount,
        exclude_from_monthly=data.exclude_from_monthly,
    )

    if await get_tag_by_slug(session, slug) is not None:
        raise ValueError(f"A tag with slug '{slug}' already exists.")

    tag = Tag(
        slug=slug,
        name=data.name.strip(),
        description=data.description,
        is_pot=data.is_pot,
        exclude_from_monthly=data.exclude_from_monthly,
        limit_amount=data.limit_amount,
        status=TagStatus.ACTIVE,
    )
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    return tag


async def list_tags(
    session: AsyncSession,
    *,
    status: TagStatus | None = None,
    is_pot: bool | None = None,
) -> Sequence[Tag]:
    query = select(Tag).order_by(Tag.name)
    if status is not None:
        query = query.where(Tag.status == status)
    if is_pot is not None:
        query = query.where(Tag.is_pot == is_pot)
    result = await session.execute(query)
    return result.scalars().all()


async def get_tag(session: AsyncSession, tag_id: uuid.UUID) -> Tag | None:
    return await session.get(Tag, tag_id)


async def get_tag_by_slug(session: AsyncSession, slug: str) -> Tag | None:
    result = await session.execute(select(Tag).where(Tag.slug == slug))
    return result.scalar_one_or_none()


async def update_tag(
    session: AsyncSession, tag_id: uuid.UUID, updates: dict
) -> Tag | None:
    """Apply `updates` to a tag. `slug` and `status` are not updatable here."""
    tag = await session.get(Tag, tag_id)
    if tag is None:
        return None

    for immutable in ("slug", "status"):
        if immutable in updates:
            raise ValueError(f"'{immutable}' cannot be changed through update_tag.")

    # Validate against the post-update state so that clearing `is_pot` in the
    # same call that clears the pot-only fields is allowed.
    _reject_pot_fields_on_plain_tag(
        is_pot=updates.get("is_pot", tag.is_pot),
        limit_amount=updates.get("limit_amount", tag.limit_amount),
        exclude_from_monthly=updates.get(
            "exclude_from_monthly", tag.exclude_from_monthly
        ),
    )

    for key, value in updates.items():
        setattr(tag, key, value.strip() if key == "name" else value)

    await session.commit()
    await session.refresh(tag)
    return tag


async def archive_tag(session: AsyncSession, tag_id: uuid.UUID) -> Tag | None:
    """Retire a tag. Existing transactions keep the slug; it just stops being
    offered for new ones."""
    tag = await session.get(Tag, tag_id)
    if tag is None:
        return None
    tag.status = TagStatus.ARCHIVED
    await session.commit()
    await session.refresh(tag)
    return tag


async def restore_tag(session: AsyncSession, tag_id: uuid.UUID) -> Tag | None:
    tag = await session.get(Tag, tag_id)
    if tag is None:
        return None
    tag.status = TagStatus.ACTIVE
    await session.commit()
    await session.refresh(tag)
    return tag


async def count_tagged_transactions(session: AsyncSession, slug: str) -> int:
    """Uses the GIN index on `transactions.tags` (`@>`)."""
    query = (
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.tags.contains([slug]))
    )
    return (await session.execute(query)).scalar_one()


async def delete_tag(session: AsyncSession, tag_id: uuid.UUID) -> bool:
    """Hard-delete a tag, allowed only while it is unused — otherwise the slug
    would be orphaned inside transaction arrays with nothing to resolve it."""
    tag = await session.get(Tag, tag_id)
    if tag is None:
        return False

    in_use = await count_tagged_transactions(session, tag.slug)
    if in_use:
        raise ValueError(
            f"'{tag.slug}' is on {in_use} transaction(s), so it cannot be deleted. "
            "Archive it instead."
        )

    await session.delete(tag)
    await session.commit()
    return True


async def resolve_slugs(
    session: AsyncSession,
    slugs: Iterable[str],
    *,
    grandfathered: Collection[str] = (),
) -> list[str]:
    """Normalise and validate slugs before writing them onto a transaction.

    Archived tags are refused alongside unknown ones, except those in
    `grandfathered` — slugs the row already carries. Without that, archiving a
    tag would freeze every transaction wearing it, since any later edit
    re-validates the whole list.
    """
    seen: list[str] = []
    for raw in slugs:
        slug = slugify(raw)
        if slug and slug not in seen:
            seen.append(slug)

    if not seen:
        return []

    if len(seen) > MAX_TAGS_PER_TRANSACTION:
        raise ValueError(
            f"A transaction can carry at most {MAX_TAGS_PER_TRANSACTION} tags; "
            f"got {len(seen)}."
        )

    active = await list_tags(session, status=TagStatus.ACTIVE)
    active_slugs = {tag.slug for tag in active}
    allowed = active_slugs | {slugify(slug) for slug in grandfathered}

    unknown = [slug for slug in seen if slug not in allowed]
    if unknown:
        available = ", ".join(sorted(active_slugs)) or "none defined yet"
        raise ValueError(
            f"Unknown or archived tag(s): {', '.join(unknown)}. "
            f"Active tags: {available}."
        )

    return seen


async def active_tag_reference(session: AsyncSession) -> str | None:
    """Render `- slug: description` lines for the agent's instructions, mirroring
    `ExpenseCategory.reference()` so tag guidance reads the same as category
    guidance. Returns None when no tags exist, so the caller can inject nothing
    rather than a placeholder."""
    tags = await list_tags(session, status=TagStatus.ACTIVE)
    if not tags:
        return None
    return "\n".join(f"- {tag.slug}: {tag.description or tag.name}" for tag in tags)
