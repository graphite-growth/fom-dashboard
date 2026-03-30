import logging
import os

from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, Depends
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.auth import COOKIE_NAME, create_token, get_current_user, is_domain_allowed
from app.config import oauth

router = APIRouter(prefix="/auth")


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    auth_url = os.environ.get("AUTH_URL", "")
    if auth_url:
        redirect_uri = f"{auth_url}/api/v1/auth/callback"
    else:
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("host", request.url.netloc)
        redirect_uri = f"{scheme}://{host}/api/v1/auth/callback"
    response: RedirectResponse = await oauth.google.authorize_redirect(request, redirect_uri=redirect_uri)
    return response


@router.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    try:
        token = await oauth.google.authorize_access_token(request)
        logging.info("OAuth token obtained successfully")
    except OAuthError as e:
        logging.error(f"OAuth error: {e.error} - {e.description}")
        return RedirectResponse(f"/login?error={e.error}")

    user_info = token.get("userinfo")
    if not user_info:
        return RedirectResponse("/login?error=no_user_info")

    email = user_info.get("email", "")
    if not is_domain_allowed(email):
        logging.warning(f"Domain not allowed for email: {email}")
        return RedirectResponse("/login?error=domain_not_allowed")

    jwt_token = create_token(dict(user_info))
    # Redirect to Next.js route handler to set cookie (Vercel Python functions
    # don't reliably forward Set-Cookie headers on redirects)
    from urllib.parse import urlencode
    params = urlencode({"token": jwt_token})
    return RedirectResponse(f"/api/auth/set-session?{params}")


@router.get("/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse(url="/login")
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return response


@router.get("/me")
async def me(user: dict = Depends(get_current_user)) -> dict:
    return {
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "image": user.get("picture", ""),
    }
