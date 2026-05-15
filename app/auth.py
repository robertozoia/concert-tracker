from __future__ import annotations

import time

import bcrypt
from fastapi import Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import settings

_BCRYPT_MAX_BYTES = 72
_SESSION_SALT = "concert-tracker.session.v1"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt=_SESSION_SALT)


def verify_password(plaintext: str) -> bool:
    if not plaintext or not settings.app_password_hash:
        return False
    pwd = plaintext.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(pwd, settings.app_password_hash.encode("utf-8"))
    except ValueError:
        return False


def hash_password(plaintext: str) -> str:
    pwd = plaintext.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pwd, bcrypt.gensalt()).decode("utf-8")


def make_session_token() -> str:
    return _serializer().dumps({"v": 1, "ts": int(time.time())})


def session_valid(token: str | None) -> bool:
    if not token:
        return False
    try:
        _serializer().loads(token, max_age=settings.session_max_age)
        return True
    except (BadSignature, SignatureExpired):
        return False


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get(settings.session_cookie_name)
    return session_valid(token)


def require_auth(request: Request):
    """FastAPI dependency. Redirects to /login when unauthenticated."""
    if is_authenticated(request):
        return True
    next_url = request.url.path
    if request.url.query:
        next_url = f"{next_url}?{request.url.query}"
    from urllib.parse import quote

    raise _RedirectToLogin(f"/login?next={quote(next_url)}")


class _RedirectToLogin(Exception):
    def __init__(self, location: str):
        self.location = location


def install_auth_exception_handler(app) -> None:
    @app.exception_handler(_RedirectToLogin)
    async def _handle(_request, exc: _RedirectToLogin):
        return RedirectResponse(url=exc.location, status_code=303)
