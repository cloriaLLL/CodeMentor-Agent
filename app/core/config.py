"""CodeMentor Agent - Application configuration using Pydantic Settings.

Modernized configuration management:
- Type-safe settings with validation
- Automatic .env loading
- Immutable frozen config (prevents accidental modification)
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    app_name: str = "CodeMentor Agent MVP"
    app_version: str = "0.2.0-modernized"
    app_description: str = "学→练→用 标准化节拍学习智能体"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # LLM Provider
    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    zhipu_api_key: Optional[str] = Field(default=None, alias="ZHIPU_API_KEY")
    zhipu_model: str = Field(default="glm-4-flash", alias="ZHIPU_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434/v1", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen2.5-coder:7b", alias="OLLAMA_MODEL")
    llm_timeout: float = Field(default=60.0, alias="LLM_TIMEOUT")
    llm_temperature: float = Field(default=0.7, alias="LLM_TEMPERATURE")

    # Retry
    max_retry: int = Field(default=3, alias="MAX_RETRY")

    # CORS
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = Field(default_factory=lambda: ["GET", "POST"])
    cors_allow_headers: list[str] = Field(default_factory=lambda: ["*"])

    # Paths
    seed_data_path: Path = Field(default=BASE_DIR / "schemas" / "seed_data.json")
    prompts_dir: Path = Field(default=BASE_DIR / "prompts")
    static_dir: Path = Field(default=BASE_DIR / "static")

    # Sandbox
    sandbox_timeout: int = Field(default=10, alias="SANDBOX_TIMEOUT")

    # Compiler (DOC-05 通用简易编译器集成)
    compiler_enabled: bool = Field(default=True, alias="COMPILER_ENABLED")
    compiler_max_source_len: int = Field(default=50000, alias="COMPILER_MAX_SOURCE_LEN")
    compiler_max_ast_depth: int = Field(default=64, alias="COMPILER_MAX_AST_DEPTH")
    compiler_timeout: float = Field(default=5.0, alias="COMPILER_TIMEOUT")
    compiler_cache_size: int = Field(default=256, alias="COMPILER_CACHE_SIZE")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance (singleton pattern via lru_cache).

    Also syncs critical LLM settings to os.environ so that llm_client.py
    (which uses os.getenv) can read them correctly — pydantic-settings reads
    .env but does NOT auto-push values into process environment.
    """
    settings = Settings()
    import os

    if settings.llm_provider:
        os.environ["LLM_PROVIDER"] = settings.llm_provider
    if settings.zhipu_api_key:
        os.environ["ZHIPU_API_KEY"] = settings.zhipu_api_key
    if settings.zhipu_model:
        os.environ["ZHIPU_MODEL"] = settings.zhipu_model
    if settings.ollama_base_url:
        os.environ["OLLAMA_HOST"] = settings.ollama_base_url.replace("/v1", "")
        os.environ["OLLAMA_BASE_URL"] = settings.ollama_base_url
    if settings.ollama_model:
        os.environ["OLLAMA_MODEL"] = settings.ollama_model
    if settings.llm_timeout:
        os.environ["LLM_TIMEOUT"] = str(settings.llm_timeout)
    return settings
