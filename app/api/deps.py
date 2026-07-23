"""CodeMentor Agent - FastAPI dependency injection utilities."""
from __future__ import annotations

from fastapi import Request

from app.core.container import AppContainer


def get_container_from_request(request: Request) -> AppContainer:
    """FastAPI dependency to get AppContainer from app state.

    Usage:
        @router.get("/")
        async def handler(container: AppContainer = Depends(get_container_from_request)):
            ...
    """
    return request.app.state.container
