import uuid

from db.models import TagStatus
from db.session import get_session
from fastapi import APIRouter, Depends, HTTPException, Query
from schema.tag import TagCreate, TagRead, TagUpdate
from services import tags as tag_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/", response_model=TagRead)
async def create_tag(
    tag: TagCreate,
    session: AsyncSession = Depends(get_session),
):
    try:
        return await tag_service.create_tag(session, tag)
    except ValueError as exc:
        # Duplicate slug, or pot-only fields set on a plain tag.
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/list/", response_model=list[TagRead])
async def get_tag_list(
    *,
    status: TagStatus | None = Query(None, description="Filter by tag status"),
    is_pot: bool | None = Query(None, description="Filter to pots, or to plain tags"),
    session: AsyncSession = Depends(get_session),
):
    return await tag_service.list_tags(session, status=status, is_pot=is_pot)


@router.get("/{tag_id}/", response_model=TagRead)
async def get_tag(tag_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    tag = await tag_service.get_tag(session, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.patch("/{tag_id}/", response_model=TagRead)
async def update_tag(
    tag_id: uuid.UUID,
    tag_update: TagUpdate,
    session: AsyncSession = Depends(get_session),
):
    # `exclude_unset` so an explicit `limit_amount: null` clears the limit,
    # rather than reading as "unchanged".
    try:
        tag = await tag_service.update_tag(
            session, tag_id, tag_update.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.post("/{tag_id}/archive/", response_model=TagRead)
async def archive_tag(tag_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Retire a tag. Transactions keep the slug; it just stops being offered."""
    tag = await tag_service.archive_tag(session, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.post("/{tag_id}/restore/", response_model=TagRead)
async def restore_tag(tag_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    tag = await tag_service.restore_tag(session, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.delete("/{tag_id}/", status_code=204)
async def delete_tag(
    tag_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    try:
        deleted = await tag_service.delete_tag(session, tag_id)
    except ValueError as exc:
        # Still in use — the caller should archive instead.
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Tag not found")
