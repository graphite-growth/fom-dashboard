import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Request

AUTH_SECRET = os.environ.get("AUTH_SECRET", "")
if not AUTH_SECRET:
    raise RuntimeError("AUTH_SECRET environment variable must be set")
ALLOWED_DOMAIN = os.environ.get("ALLOWED_DOMAIN", "graphitehq.com")
COOKIE_NAME = "session_token"
TOKEN_EXPIRY_HOURS = 24


def is_domain_allowed(email: str) -> bool:
    if not ALLOWED_DOMAIN:
        return True
    domain = email.rsplit("@", 1)[-1]
    return domain == ALLOWED_DOMAIN


def create_token(user_info: dict) -> str:
    payload = {
        "sub": user_info.get("sub", ""),
        "name": user_info.get("name", ""),
        "email": user_info.get("email", ""),
        "picture": user_info.get("picture", ""),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, AUTH_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict[str, object]:
    try:
        payload: dict[str, object] = jwt.decode(token, AUTH_SECRET, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(request: Request) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return decode_token(token)
