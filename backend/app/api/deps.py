from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.session import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def verify_internal_token(x_internal_token: Annotated[str, Header()]):
    if x_internal_token != settings.INTERNAL_API_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")
