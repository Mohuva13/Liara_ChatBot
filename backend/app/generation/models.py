from typing import Literal

from pydantic import BaseModel, Field


class GroundedClaim(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    source_ids: list[str] = Field(min_length=1, max_length=8)


class GroundedAnswer(BaseModel):
    answer_markdown: str = Field(min_length=1, max_length=20000)
    claims: list[GroundedClaim] = Field(min_length=1, max_length=30)
    suggestions: list[str] = Field(default_factory=list, max_length=4)
    outcome: Literal["answered"]


class ValidatedAnswer(BaseModel):
    answer_markdown: str
    source_ids: list[str]
    suggestions: list[str]
