import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from schema.person import PersonCreate, PersonRead, PersonUpdate
from services import people as people_service

router = APIRouter()


@router.post("/", response_model=PersonRead)
async def create_person(
    person: PersonCreate,
    session: AsyncSession = Depends(get_session),
):
    try:
        return await people_service.create_person(session, person)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/list/", response_model=list[PersonRead])
async def get_person_list(session: AsyncSession = Depends(get_session)):
    return await people_service.list_people(session)


@router.get("/{person_id}/", response_model=PersonRead)
async def get_person(
    person_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    person = await people_service.get_person(session, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@router.patch("/{person_id}/", response_model=PersonRead)
async def update_person(
    person_id: uuid.UUID,
    person_update: PersonUpdate,
    session: AsyncSession = Depends(get_session),
):
    try:
        person = await people_service.update_person(
            session, person_id, person_update.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@router.delete("/{person_id}/", status_code=204)
async def delete_person(
    person_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    try:
        deleted = await people_service.delete_person(session, person_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Person not found")
