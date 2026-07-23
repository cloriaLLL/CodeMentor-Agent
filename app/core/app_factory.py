"""CodeMentor Agent - FastAPI application factory with lifespan management."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import Settings, get_settings, BASE_DIR
from app.core.container import AppContainer, get_container
from app.core.exceptions import AppError
from app.core.logger import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifecycle: startup and shutdown events.

    - Startup: Initialize container, warm up caches, configure logging
    - Shutdown: Clean up resources gracefully
    """
    settings: Settings = app.state.settings
    container: AppContainer = app.state.container

    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        llm_provider=settings.llm_provider,
    )

    seed_data = container.load_seed_data()
    _ = container.orchestrator

    # Initialize database and load builtin problems
    from app.core.database import get_db
    db = get_db()
    db.init_db()

    from app.services.problem_fetcher import ProblemFetcherService
    fetcher = ProblemFetcherService()
    fetcher.load_builtin_problems()

    logger.info(
        "application_started",
        host=settings.host,
        port=settings.port,
        seed_data_loaded=bool(seed_data),
    )

    yield

    logger.info("application_shutting_down")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure FastAPI application instance (factory pattern).

    Uses dependency injection pattern with explicit settings and container,
    making testing and configuration easier.

    Args:
        settings: Optional settings override (for testing).

    Returns:
        Configured FastAPI application instance.
    """
    if settings is None:
        settings = get_settings()

    setup_logging(debug=settings.debug)

    container = get_container()
    if settings is not get_settings():
        container.settings = settings
        container.reset()

    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.container = container

    _configure_middleware(app, settings)
    _configure_exception_handlers(app)
    _register_routes(app)
    _configure_static_files(app, settings)

    return app


def _configure_middleware(app: FastAPI, settings: Settings) -> None:
    """Configure CORS and other middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )


def _configure_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers that return structured JSON errors."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("app_error", error_code=exc.code, message=exc.message, path=request.url.path)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "code": exc.status_code,
                "error_code": exc.code,
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Internal server error",
                "code": 500,
            },
        )


def _configure_static_files(app: FastAPI, settings: Settings) -> None:
    """Mount static file directory and configure SPA frontend serving."""
    static_dir: Path = settings.static_dir
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Serve Vite-built frontend (frontend/dist) as SPA
    frontend_dist = BASE_DIR / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="frontend-assets")
        dist_root = frontend_dist.resolve()

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):
            """SPA fallback: serve real static files from dist root (favicon,
            icons, manifest, etc.) when present, otherwise serve index.html for
            client-side routing. API and /static paths are excluded.
            """
            if full_path.startswith("api/") or full_path.startswith("static/") or full_path.startswith("assets/"):
                raise HTTPException(status_code=404)
            # Serve a real file from the dist root if it exists (path-traversal safe).
            if full_path:
                try:
                    candidate = (frontend_dist / full_path).resolve()
                except (ValueError, OSError):
                    candidate = None
                if candidate is not None and dist_root in (candidate, *candidate.parents) and candidate.is_file():
                    return FileResponse(str(candidate))
            index_file = frontend_dist / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
            return RedirectResponse(url="/static/index.html")
    else:
        @app.get("/", include_in_schema=False)
        async def root_redirect() -> RedirectResponse:
            return RedirectResponse(url="/static/index.html")


def _register_routes(app: FastAPI) -> None:
    """Register all API routes from modular router modules."""
    from app.api import health, teach, chat, llm, learn, exercise, conversation, compiler

    app.include_router(health.router, tags=["health"])
    app.include_router(teach.router, prefix="/api", tags=["teach"])
    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(llm.router, prefix="/api", tags=["llm"])
    app.include_router(learn.router, prefix="/api", tags=["learn"])
    app.include_router(exercise.router, prefix="/api", tags=["exercise"])
    app.include_router(conversation.router, prefix="/api", tags=["conversation"])
    app.include_router(compiler.router, prefix="/api", tags=["compiler"])
