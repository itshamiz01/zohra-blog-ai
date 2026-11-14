"""
ZOHRA AUTONOMOUS PUBLISHING ENGINE — Application Entry Point

This is the FastAPI application factory. It:
  - configures CORS
  - registers exception handlers (safe — no secrets/stack traces to clients)
  - mounts all API routers
  - attaches startup/shutdown lifecycle hooks
  - adds request-ID correlation middleware

SECURITY RULES:
  - Exception handlers NEVER expose stack traces, DB details, or secrets
  - Request-ID propagated through every handler for debugging
  - CORS origins configurable, not wildcarded in production
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_v1_router, health_routes
from app.core.config import get_settings
from app.core.exceptions import ZohraError
from app.core.lifecycle import shutdown, startup
from app.core.security import REQUEST_ID_HEADER

# ── Lifespan ─────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Async context manager for startup/shutdown lifecycle."""
    await startup()
    yield
    await shutdown()


# ── App Factory ──────────────────────────────────────────────────


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Zohra Autonomous Publishing Engine",
        description="Production-grade autonomous content publishing platform",
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request-ID Middleware ────────────────────────────────────
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    # ── Exception Handlers ──────────────────────────────────────

    @app.exception_handler(ZohraError)
    async def zohra_error_handler(request: Request, exc: ZohraError) -> JSONResponse:
        """Handle all custom Zohra errors — safe error codes, no internals."""
        request_id = getattr(request.state, "request_id", None)

        # Map error codes to HTTP status codes
        status_map = {
            "AUTHENTICATION_ERROR": 401,
            "AUTHORIZATION_ERROR": 403,
            "VALIDATION_ERROR": 422,
            "BUDGET_EXCEEDED": 429,
            "RATE_LIMIT_EXCEEDED": 429,
            "DUPLICATE_OPERATION": 409,
            "WORKFLOW_ERROR": 400,
            "FEATURE_DISABLED": 403,
            "AUTONOMY_DISABLED": 403,
        }
        http_status = status_map.get(exc.code, 500)

        return JSONResponse(
            status_code=http_status,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                },
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Catch-all for unhandled exceptions.
        NEVER expose internal details to the client.
        """
        import logging

        logger = logging.getLogger("zohra.unhandled")
        request_id = getattr(request.state, "request_id", None)
        logger.error(
            "Unhandled exception: %s",
            exc,
            extra={"request_id": request_id},
            exc_info=True,
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                },
                "request_id": request_id,
            },
        )

    # ── Routes ──────────────────────────────────────────────────
    app.include_router(health_routes)
    app.include_router(api_v1_router)

    # ── Interactive Command Center Console (Prompt #1) ───────────
    from pathlib import Path

    from fastapi.responses import HTMLResponse

    @app.get("/console", response_class=HTMLResponse, include_in_schema=False)
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def serve_command_center():
        console_path = Path(__file__).parent / "static" / "console.html"
        if console_path.exists():
            return HTMLResponse(content=console_path.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>Zohra Publishing OS Active</h1><p>API running under /api/v1</p>")

    return app


# ── Module-level app instance ────────────────────────────────────
app = create_app()
