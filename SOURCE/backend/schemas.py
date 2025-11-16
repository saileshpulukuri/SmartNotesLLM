"""
Pydantic models for request and response validation.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=255)


class LoginRequest(BaseModel):
    username: str
    password: str


class NoteCreateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)


class NoteUpdateRequest(BaseModel):
    topic: Optional[str] = Field(default=None, max_length=255)
    message: Optional[str] = Field(default=None)


class NoteResponse(BaseModel):
    note_id: int
    topic: str
    message: str
    last_update: dt.datetime
    display_number: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class NLQueryRequest(BaseModel):
    query: str = Field(min_length=1, description="Natural language command from user")


class NLQueryResponse(BaseModel):
    action: str
    result: dict


__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "NoteCreateRequest",
    "NoteUpdateRequest",
    "NoteResponse",
    "NLQueryRequest",
    "NLQueryResponse",
]

