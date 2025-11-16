"""
Authentication helpers for password hashing and JWT management.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash, generate_password_hash

from .config import get_settings


settings = get_settings()


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


def create_jwt(identity: Any) -> str:
    expires = dt.timedelta(minutes=settings.access_token_expires_minutes)
    return create_access_token(identity=str(identity), expires_delta=expires)


__all__ = ["hash_password", "verify_password", "create_jwt"]

