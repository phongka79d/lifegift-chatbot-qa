"""Chat API endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.auth import get_optional_current_user
from backend.app.chatbot.service import ChatbotService
from backend.app.core.database import get_db
from backend.app.repositories.chat_repository import ChatRepository
from backend.app.schemas.chat import ChatRequest, ChatResponse, ChatSessionResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a chat message and receive grounded answers and product cards",
)
async def chat_endpoint(
    request: ChatRequest,
    user_id: Optional[int] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Handle chat interaction, extracting intent and returning grounded responses."""
    try:
        service = ChatbotService(session=db)
        response = await service.handle_chat(request, user_id=user_id)
        return response
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Error processing chat message: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request.",
        )


@router.get(
    "/chat/sessions/{session_id}",
    response_model=ChatSessionResponse,
    summary="Retrieve chat history for a session",
)
async def get_session_endpoint(
    session_id: int,
    user_id: Optional[int] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve chat session history verifying ownership if authenticated."""
    repo = ChatRepository(db)
    try:
        session = repo.get_session(session_id=session_id, user_id=user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat session {session_id} not found.",
            )
        return session
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this chat session is denied.",
        )
