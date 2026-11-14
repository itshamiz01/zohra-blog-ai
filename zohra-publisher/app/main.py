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

    # ── Installable PWA (manifest, icons, service worker, /install) ──
    from io import BytesIO

    from fastapi.responses import Response

    _PWA_GREEN = (18, 59, 42)     # #123B2A
    _PWA_GOLD = (201, 162, 39)    # #C9A227
    _icon_cache: dict = {}

    def _draw_icon_png(size: int, maskable: bool = False) -> bytes:
        """Gold Z on deep green, drawn at runtime with Pillow (no binary assets)."""
        from PIL import Image, ImageDraw

        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        if maskable:
            d.rectangle([0, 0, size, size], fill=_PWA_GREEN + (255,))
            pad = size * 0.26
        else:
            d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.22),
                                fill=_PWA_GREEN + (255,))
            pad = size * 0.24
        x0, y0, x1, y1 = pad, pad, size - pad, size - pad
        bar = (y1 - y0) * 0.20
        diag = (x1 - x0) * 0.20
        d.rectangle([x0, y0, x1, y0 + bar], fill=_PWA_GOLD + (255,))
        d.rectangle([x0, y1 - bar, x1, y1], fill=_PWA_GOLD + (255,))
        d.polygon([(x1 - diag, y0 + bar), (x1, y0 + bar),
                   (x0 + diag, y1 - bar), (x0, y1 - bar)], fill=_PWA_GOLD + (255,))
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _icon_response(size: int, maskable: bool = False) -> Response:
        key = (size, maskable)
        if key not in _icon_cache:
            _icon_cache[key] = _draw_icon_png(size, maskable)
        return Response(content=_icon_cache[key], media_type="image/png",
                        headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/icons/icon-192.png", include_in_schema=False)
    async def pwa_icon_192():
        return _icon_response(192)

    @app.get("/icons/icon-512.png", include_in_schema=False)
    async def pwa_icon_512():
        return _icon_response(512)

    @app.get("/icons/maskable-512.png", include_in_schema=False)
    async def pwa_icon_maskable():
        return _icon_response(512, maskable=True)

    @app.get("/apple-touch-icon.png", include_in_schema=False)
    async def pwa_apple_icon():
        return _icon_response(180, maskable=True)

    @app.get("/manifest.webmanifest", include_in_schema=False)
    async def pwa_manifest():
        return JSONResponse(
            content={
                "name": "Zohra Blog AI",
                "short_name": "Zohra Blog",
                "description": "Zohra Autonomous Publishing OS — command center",
                "start_url": "/",
                "scope": "/",
                "display": "standalone",
                "background_color": "#FAF9F5",
                "theme_color": "#123B2A",
                "icons": [
                    {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                    {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
                    {"src": "/icons/maskable-512.png", "sizes": "512x512", "type": "image/png",
                     "purpose": "maskable"},
                ],
            },
            media_type="application/manifest+json",
        )

    @app.get("/sw.js", include_in_schema=False)
    async def pwa_service_worker():
        js = (
            "const CACHE='zohra-blog-v1';"
            "const SHELL=['/','/install','/manifest.webmanifest','/icons/icon-192.png','/icons/icon-512.png'];"
            "self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()))});"
            "self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});"
            "self.addEventListener('fetch',e=>{const u=new URL(e.request.url);"
            "if(e.request.method!=='GET'||u.pathname.startsWith('/api')||u.pathname.startsWith('/health'))return;"
            "if(e.request.mode==='navigate'){e.respondWith(fetch(e.request).then(r=>{const cp=r.clone();caches.open(CACHE).then(c=>c.put(e.request,cp));return r}).catch(()=>caches.match(e.request)));return}"
            "e.respondWith(caches.match(e.request).then(h=>h||fetch(e.request)))});"
        )
        return Response(content=js, media_type="application/javascript",
                        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})

    @app.get("/install", response_class=HTMLResponse, include_in_schema=False)
    async def serve_install_page():
        install_path = Path(__file__).parent / "static" / "install.html"
        if install_path.exists():
            return HTMLResponse(content=install_path.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>Install Zohra Blog AI</h1><p>Open this site in Chrome and choose Install app.</p>")

    return app


# ── Module-level app instance ────────────────────────────────────
app = create_app()
