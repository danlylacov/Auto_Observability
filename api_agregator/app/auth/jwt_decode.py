"""Decode JWT issued by users_api (shared secret)."""

import jwt

from app.config import get_settings


def decode_access_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(
        token,
        s.jwt_secret,
        algorithms=[s.jwt_algorithm],
        options={"require": ["exp", "sub", "role"]},
    )
