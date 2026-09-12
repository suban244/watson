from typing import Annotated
from uuid import UUID

from pydantic import PlainSerializer

# CodeMode's sandbox (Monty) rejects UUIDs, and the harness dumps tool results
# in python mode, so ids on anything a tool returns must serialize as strings.
StrUUID = Annotated[UUID, PlainSerializer(str, return_type=str)]
