"""Teach and Ecosystem mode endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_container_from_request
from app.core.container import AppContainer
from app.core.exceptions import NodeNotFoundError
from app.schemas import (
    TeachRequest,
    TeachResponse,
    EcosystemSummaryRequest,
    EcosystemSummaryResponse,
    CrossLanguageEquivalent,
)

router = APIRouter()


@router.post("/teach", response_model=TeachResponse)
async def teach(
    req: TeachRequest,
    container: AppContainer = Depends(get_container_from_request),
) -> TeachResponse:
    """State 1: TeachMode - Knowledge explanation via OrchestratorAgent."""
    try:
        content = container.orchestrator.teach(req.node_id)
    except ValueError:
        raise NodeNotFoundError(req.node_id)

    return TeachResponse(
        status="success",
        state="TeachMode",
        markdown_content=content.markdown_content,
        grounding_source=content.grounding_source,
        history_notes=content.history_notes,
        next_actions=content.next_actions,
    )


@router.post("/ecosystem_summary", response_model=EcosystemSummaryResponse)
async def ecosystem_summary(
    req: EcosystemSummaryRequest,
    container: AppContainer = Depends(get_container_from_request),
) -> EcosystemSummaryResponse:
    """State 3: EcosystemMode - Industry ecosystem summary."""
    try:
        content = container.orchestrator.ecosystem_summary(req.node_id)
    except ValueError:
        raise NodeNotFoundError(req.node_id)

    cross_lang = content.cross_language_equivalent

    return EcosystemSummaryResponse(
        status="success",
        state="EcosystemMode",
        stack_summary=content.stack_summary,
        cross_language_equivalent=CrossLanguageEquivalent(
            Go=cross_lang.get("Go", ""),
        ),
        next_node_recommendation=content.next_node_recommendation,
    )
