"""CodeMentor Agent - Modernized FastAPI application entry point.

Architecture upgraded to modern layered design:
- app/core/: Configuration, logging, DI container, app factory, exceptions
- app/schemas/: Pydantic request/response models (type-safe)
- app/services/: Business logic services
- app/api/: Modular route handlers with FastAPI dependency injection
- agents/, sandbox.py: Legacy modules preserved for compatibility

Backward compatibility: All existing API endpoints remain unchanged.
"""
from __future__ import annotations

from app.core.app_factory import create_app

app = create_app()


if __name__ == "__main__":
    import uvicorn
    from app.core.config import get_settings

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
