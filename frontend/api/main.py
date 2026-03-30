import os

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from app.auth import COOKIE_NAME, create_token
from app.routes import auth, dashboard, health, hello

app = FastAPI()


class StripApiPrefixMiddleware(BaseHTTPMiddleware):
    """Strip /api/v1 prefix so FastAPI routes match without it."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.scope.get("path", "")
        if path.startswith("/api/v1"):
            request.scope["path"] = path.removeprefix("/api/v1") or "/"
        return await call_next(request)


app.add_middleware(StripApiPrefixMiddleware)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("AUTH_SECRET", ""),
    same_site="lax",
    https_only=os.environ.get("AUTH_URL", "").startswith("https"),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin
        for origin in [
            "http://localhost:3000",
            os.environ.get("AUTH_URL", ""),
        ]
        if origin
    ],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Content-Type", "Accept"],
)

if os.environ.get("DEV_AUTH", "").lower() == "true":

    @app.middleware("http")
    async def dev_auth_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not request.cookies.get(COOKIE_NAME):
            token = create_token(
                {
                    "sub": "dev",
                    "name": "Dev User",
                    "email": "dev@example.com",
                    "picture": "",
                }
            )
            redirect_url = os.environ.get("AUTH_URL", str(request.url))
            response = RedirectResponse(redirect_url)
            response.set_cookie(
                key=COOKIE_NAME,
                value=token,
                httponly=True,
                samesite="lax",
                secure=os.environ.get("AUTH_URL", "").startswith("https"),
                path="/",
            )
            return response
        return await call_next(request)


app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(health.router)
app.include_router(hello.router)
