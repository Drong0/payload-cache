from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

# Upper bounds keep a single request from fanning out into an unbounded number
# of calls to the transformer service.
MAX_ITEMS_PER_LIST = 1000
MAX_STRING_LENGTH = 1000

BoundedStr = Annotated[str, StringConstraints(max_length=MAX_STRING_LENGTH)]
BoundedList = Annotated[list[BoundedStr], Field(min_length=1, max_length=MAX_ITEMS_PER_LIST)]


class PayloadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    list_1: BoundedList
    list_2: BoundedList

    @model_validator(mode="after")
    def check_same_length(self) -> Self:
        if len(self.list_1) != len(self.list_2):
            raise ValueError("list_1 and list_2 must have the same length")
        return self


class PayloadCreated(BaseModel):
    id: UUID
    message: str


class PayloadRead(BaseModel):
    output: str
