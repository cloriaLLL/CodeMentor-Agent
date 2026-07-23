"""Pytest fixtures for CodeMentor Agent.

Forces Mock LLM so the full route suite runs hermetically — no network access
and no Zhipu API key required. Environment overrides are applied at module
import time (before any app module reads settings) and the cached singletons
are cleared in the ``app`` fixture so the overrides take effect.
"""
from __future__ import annotations

import os

# --- Force Mock LLM BEFORE any app import (env vars win over .env file) ---
os.environ["LLM_PROVIDER"] = "mock"
os.environ["ZHIPU_API_KEY"] = ""
os.environ.pop("OLLAMA_HOST", None)

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def app():
    """Build a fresh FastAPI app with the Mock LLM override applied."""
    # Clear cached singletons so the env overrides above take effect.
    from app.core.config import get_settings
    from app.core.container import get_container

    get_settings.cache_clear()
    get_container.cache_clear()

    from app.core.app_factory import create_app

    return create_app()


@pytest.fixture(scope="session")
def client(app):
    """Starlette TestClient — entering the context runs the app lifespan."""
    with TestClient(app) as c:
        yield c
