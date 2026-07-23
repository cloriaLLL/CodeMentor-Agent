"""CodeMentor Agent - Custom exceptions for the application."""
from __future__ import annotations


class AppError(Exception):
    """Base exception for application errors with HTTP status code."""

    def __init__(self, message: str, status_code: int = 500, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class NodeNotFoundError(AppError):
    """Raised when a knowledge node is not found."""

    def __init__(self, node_id: str):
        super().__init__(
            message=f"Knowledge node not found: {node_id}",
            status_code=404,
            code="NODE_NOT_FOUND",
        )
