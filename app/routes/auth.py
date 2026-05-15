from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..auth import is_authenticated, make_session_token, verify_password
from ..config import settings
from ..templating import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, next: str | None = None):
    if is_authenticated(request):
        return RedirectResponse(url=next or "/", status_code=303)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": None, "next": next or "/"},
    )


@router.post("/login")
def login_submit(
    request: Request,
    password: str = Form(...),
    next: str = Form("/"),
):
    if not verify_password(password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Contraseña incorrecta", "next": next},
            status_code=401,
        )

    safe_next = next if next.startswith("/") else "/"
    response = RedirectResponse(url=safe_next, status_code=303)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=make_session_token(),
        max_age=settings.session_max_age,
        httponly=True,
        samesite="lax",
        secure=False,  # behind Caddy TLS terminator; the browser still gets the cookie.
        path="/",
    )
    return response


@router.post("/logout")
def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(settings.session_cookie_name, path="/")
    return response
