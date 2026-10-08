"""Fizzy API shapes, trimmed to what the agent needs.

Fizzy returns far more than this; extra fields are ignored so tool results stay
small. Timestamps stay as strings — they are only ever shown, never computed on.
"""

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class FizzyModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class FizzyUser(FizzyModel):
    id: str
    name: str


class FizzyTag(FizzyModel):
    id: str
    title: str


class FizzyColumn(FizzyModel):
    id: str
    name: str


class FizzyBoardRef(FizzyModel):
    id: str
    name: str


class FizzyBoard(FizzyBoardRef):
    columns: list[FizzyColumn] = []


class FizzyStep(FizzyModel):
    id: str
    content: str
    completed: bool


class FizzyCard(FizzyModel):
    number: int
    title: str
    description: str | None = None
    board: FizzyBoardRef | None = None
    # None while the card sits in triage ("Maybe?").
    column: FizzyColumn | None = None
    tags: list[str] = []
    assignees: list[FizzyUser] = []
    steps: list[FizzyStep] = []
    closed: bool = False
    postponed: bool = False
    golden: bool = False
    last_active_at: str | None = None
    url: str

    @computed_field
    @property
    def lane(self) -> str:
        if self.closed:
            return "Done"
        if self.postponed:
            return "Not Now"
        return self.column.name if self.column else "Maybe?"


class FizzyComment(FizzyModel):
    id: str
    creator: FizzyUser
    body: str
    created_at: str

    @field_validator("body", mode="before")
    @classmethod
    def _plain_text(cls, value):
        if isinstance(value, dict):
            return value.get("plain_text", "")
        return value


class FizzyCardDetail(FizzyCard):
    comments: list[FizzyComment] = Field(default_factory=list)
