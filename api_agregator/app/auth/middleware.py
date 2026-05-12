"""HTTP middleware: JWT + role checks for /api/v1/* on api_agregator."""

import logging
import os

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.auth.jwt_decode import decode_access_token
from app.auth.permissions import is_request_allowed

logger = logging.getLogger(__name__)

EXEMPT_PATHS = frozenset({"/", "/health", "/favicon.ico"})
EXEMPT_PREFIXES = ("/docs", "/openapi.json", "/redoc")


class JwtAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        path = request.url.path
        if request.method == "OPTIONS":
            return await call_next(request)
        if path in EXEMPT_PATHS:
            return await call_next(request)
        if path.startswith(EXEMPT_PREFIXES):
            return await call_next(request)
        if not path.startswith("/api/v1"):
            return await call_next(request)

        if os.getenv("SKIP_JWT_AUTH", "").lower() in ("1", "true", "yes"):
            return await call_next(request)

        auth = request.headers.get("authorization")
        if not auth or not auth.lower().startswith("bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Not authenticated"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = auth.split(" ", 1)[1].strip()
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Not authenticated"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            payload = decode_access_token(token)
        except Exception as exc:
            logger.debug("JWT decode failed: %s", exc)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        role = payload.get("role")
        if not isinstance(role, str):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid token"},
            )

        if not is_request_allowed(request.method, path, role):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Insufficient permissions"},
            )

        request.state.jwt_payload = payload
        return await call_next(request)
