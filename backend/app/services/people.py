import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Person
from schema.person import PersonCreate
from services.tags import slugify


def _normalise_nickname(value: str) -> str:
    nickname = slugify(value)
    if not nickname:
        raise ValueError(f"Could not make a nickname out of '{value}'.")
    return nickname


def _clean_full_name(value: str | None) -> str | None:
    return (value or "").strip() or None


async def _ensure_nickname_free(
    session: AsyncSession, nickname: str, *, exclude_id: uuid.UUID | None = None
) -> None:
    existing = await get_person_by_nickname(session, nickname)
    if existing is not None and existing.id != exclude_id:
        taken_by = f" ({existing.full_name})" if existing.full_name else ""
        raise ValueError(
            f"The nickname '{nickname}' is taken{taken_by}. Pick another one for "
            "this person."
        )


async def create_person(session: AsyncSession, data: PersonCreate) -> Person:
    nickname = _normalise_nickname(data.nickname)
    await _ensure_nickname_free(session, nickname)

    person = Person(
        nickname=nickname,
        full_name=_clean_full_name(data.full_name),
        meta=data.meta,
    )
    session.add(person)
    await session.commit()
    await session.refresh(person)
    return person


async def list_people(session: AsyncSession) -> Sequence[Person]:
    result = await session.execute(select(Person).order_by(Person.nickname))
    return result.scalars().all()


async def get_person(session: AsyncSession, person_id: uuid.UUID) -> Person | None:
    return await session.get(Person, person_id)


async def get_person_by_nickname(session: AsyncSession, nickname: str) -> Person | None:
    result = await session.execute(
        select(Person).where(Person.nickname == slugify(nickname))
    )
    return result.scalar_one_or_none()


async def resolve_person(
    session: AsyncSession, ref: str, *, create: bool = False
) -> Person | None:
    """Find a person by nickname, then by full name; optionally create them."""
    nickname = _normalise_nickname(ref)

    person = await get_person_by_nickname(session, nickname)
    if person is not None:
        return person

    result = await session.execute(
        select(Person).where(func.lower(Person.full_name) == ref.strip().lower())
    )
    matches = result.scalars().all()
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        nicknames = ", ".join(match.nickname for match in matches)
        raise ValueError(
            f"More than one person is called {matches[0].full_name}: {nicknames}. "
            "Use the nickname."
        )

    if not create:
        return None
    return await create_person(session, PersonCreate(nickname=nickname))


async def update_person(
    session: AsyncSession, person_id: uuid.UUID, updates: dict
) -> Person | None:
    """`meta` replaces the whole bag; use `set_detail` to change one key."""
    person = await session.get(Person, person_id)
    if person is None:
        return None

    if "nickname" in updates:
        updates["nickname"] = _normalise_nickname(updates["nickname"] or "")
        await _ensure_nickname_free(session, updates["nickname"], exclude_id=person.id)
    if "full_name" in updates:
        updates["full_name"] = _clean_full_name(updates["full_name"])

    for key, value in updates.items():
        setattr(person, key, value)

    await session.commit()
    await session.refresh(person)
    return person


async def set_detail(
    session: AsyncSession, person_id: uuid.UUID, key: str, value: object
) -> Person | None:
    """Write one key into a person's `meta`, leaving the rest alone."""
    person = await session.get(Person, person_id)
    if person is None:
        return None

    if person.meta is None:
        person.meta = {key: value}
    else:
        person.meta[key] = value

    await session.commit()
    await session.refresh(person)
    return person


async def delete_person(session: AsyncSession, person_id: uuid.UUID) -> bool:
    person = await session.get(Person, person_id)
    if person is None:
        return False

    nickname = person.nickname

    try:
        await session.delete(person)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ValueError(
            f"{nickname} still has ledger entries, so they cannot be deleted."
        ) from exc

    return True


async def person_reference(session: AsyncSession) -> str | None:
    people = await list_people(session)
    if not people:
        return None
    return "\n".join(
        f"- {person.nickname}: {person.full_name}"
        if person.full_name
        else f"- {person.nickname}"
        for person in people
    )
