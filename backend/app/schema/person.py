"""Person schemas."""

from pydantic import BaseModel, ConfigDict

from schema.types import StrUUID


class PersonBase(BaseModel):
    full_name: str | None = None
    meta: dict | None = None


class PersonCreate(PersonBase):
    nickname: str


class PersonRead(PersonBase):
    id: StrUUID
    nickname: str

    model_config = ConfigDict(from_attributes=True)


class PersonUpdate(BaseModel):
    """Callers should dump with `exclude_unset=True`, so an explicit
    `full_name: null` clears it. `meta` replaces the whole bag; `set_detail` in
    the service is the way to change one key.
    """

    nickname: str | None = None
    full_name: str | None = None
    meta: dict | None = None
