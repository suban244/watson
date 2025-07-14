# from schema.transaction import (
#     TagCreate,
#     TagRead,
# )
# from fastapi import APIRouter, Depends
# from db.models import Tag
# from db.session import get_session
# from sqlalchemy import select

# from sqlalchemy.ext.asyncio import AsyncSession

# router = APIRouter()


# async def get_all_tags(session: AsyncSession = Depends(get_session)) -> list[Tag]:
#     get_all_tags_query = select(Tag)
#     result = await session.execute(get_all_tags_query)
#     tags = result.scalars().all()
#     return list(tags)


# @router.post("/", response_model=TagRead)
# async def create_tag(tag: TagCreate, session: AsyncSession = Depends(get_session)):
#     new_tag = Tag(**tag.model_dump())
#     session.add(new_tag)
#     await session.commit()
#     return new_tag


# @router.get("/list/", response_model=list[TagRead])
# async def get_tag_list(tags: list[Tag] = Depends(get_all_tags)):
#     return tags
