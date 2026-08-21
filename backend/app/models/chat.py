from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatStreamRequest(BaseModel):
    protocol_version: Literal["1"]
    session_id: str = Field(min_length=20, max_length=128)
    message_id: str = Field(min_length=8, max_length=128)
    text: str = Field(min_length=1)
    surface: Literal["popup", "page"]
    locale: Literal["fa-IR"]

    @field_validator("session_id", "message_id")
    @classmethod
    def validate_opaque_identifier(cls, value: str) -> str:
        if not all(character.isalnum() or character in "-_" for character in value):
            raise ValueError("identifier contains unsupported characters")
        return value

    @field_validator("text")
    @classmethod
    def normalize_input_boundary(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message text cannot be blank")
        return value


class SessionResponse(BaseModel):
    session_id: str
    expires_in_seconds: int
