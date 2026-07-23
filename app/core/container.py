"""CodeMentor Agent - Dependency injection container.

Manages singleton instances of agents and services with proper lifecycle.
Replaces global variables in main.py with explicit dependency management.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.core.config import Settings, get_settings
from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AppContainer:
    """Application dependency container holding all singleton services."""

    settings: Settings
    _orchestrator: Optional[object] = field(default=None, init=False)
    _seed_data_cache: Optional[dict] = field(default=None, init=False)
    _learning_state: Optional[object] = field(default=None, init=False)
    _exercise_service: Optional[object] = field(default=None, init=False)
    _problem_fetcher: Optional[object] = field(default=None, init=False)
    _conv_store: Optional[object] = field(default=None, init=False)
    _compiler_service: Optional[object] = field(default=None, init=False)

    def __post_init__(self) -> None:
        logger.info(
            "app_container_initialized",
            llm_provider=self.settings.llm_provider,
            debug=self.settings.debug,
        )

    @property
    def orchestrator(self):
        """Lazy-loaded OrchestratorAgent singleton."""
        if self._orchestrator is None:
            from agents.orchestrator import OrchestratorAgent
            self._orchestrator = OrchestratorAgent()
            logger.debug("orchestrator_initialized")
        return self._orchestrator

    @property
    def exercise_service(self):
        """Lazy-loaded ExerciseService singleton."""
        if self._exercise_service is None:
            from app.services.exercise_service import ExerciseService
            self._exercise_service = ExerciseService()
            logger.debug("exercise_service_initialized")
        return self._exercise_service

    @property
    def problem_fetcher(self):
        """Lazy-loaded ProblemFetcherService singleton."""
        if self._problem_fetcher is None:
            from app.services.problem_fetcher import ProblemFetcherService
            self._problem_fetcher = ProblemFetcherService()
            self._problem_fetcher.load_builtin_problems()
            logger.debug("problem_fetcher_initialized")
        return self._problem_fetcher

    @property
    def conversation_store(self):
        """Lazy-loaded ConversationStore singleton."""
        if self._conv_store is None:
            from app.services.conversation_store import ConversationStore
            self._conv_store = ConversationStore()
            logger.debug("conversation_store_initialized")
        return self._conv_store

    @property
    def compiler_service(self):
        """Lazy-loaded CompilerService singleton (DOC-05 编译器集成)."""
        if self._compiler_service is None:
            from app.services.compiler_service import CompilerService
            self._compiler_service = CompilerService()
            logger.debug("compiler_service_initialized")
        return self._compiler_service

    def load_seed_data(self, force_reload: bool = False) -> dict:
        """Load and cache seed_data.json (delegates to shared cached loader).

        Args:
            force_reload: Force re-read from disk.

        Returns:
            Parsed seed_data dictionary.
        """
        if force_reload:
            from agents import load_seed_data
            load_seed_data.cache_clear()
        if self._seed_data_cache is None or force_reload:
            from agents import load_seed_data
            self._seed_data_cache = load_seed_data()
            logger.info(
                "seed_data_loaded",
                knowledge_atoms=len(self._seed_data_cache.get("knowledge_atoms", [])),
                seed_problems=len(self._seed_data_cache.get("seed_problems", [])),
            )
        return self._seed_data_cache

    def reset(self) -> None:
        """Reset all cached instances (useful for testing)."""
        self._orchestrator = None
        self._seed_data_cache = None
        self._learning_state = None
        self._exercise_service = None
        self._problem_fetcher = None
        self._conv_store = None
        self._compiler_service = None
        logger.debug("app_container_reset")


@lru_cache(maxsize=1)
def get_container() -> AppContainer:
    """Get cached application container singleton."""
    return AppContainer(settings=get_settings())
