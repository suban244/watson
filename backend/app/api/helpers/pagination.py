from typing import Annotated

from fastapi import Query
from pydantic import BaseModel


class PaginationSkipLimit(BaseModel):
    skip: int
    limit: int


class PaginationPageSize(BaseModel):
    page: int
    size: int


class Pagination:
    def __init__(self, maximum_limit: int = 500):
        self.maximum_limit = maximum_limit

    async def skip_limit(
        self,
        skip: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=0)] = 20,
    ) -> PaginationSkipLimit:
        capped_limit = min(self.maximum_limit, limit)
        return PaginationSkipLimit(skip=skip, limit=capped_limit)

    async def page_size(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=0)] = 20,
    ) -> PaginationPageSize:
        capped_size = min(self.maximum_limit, size)
        return PaginationPageSize(page=page, size=capped_size)
