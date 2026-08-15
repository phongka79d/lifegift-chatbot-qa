"""Chat Repository for session lifecycle and message persistence."""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.schemas.chat import ChatMessageItem, ChatSessionResponse


class ChatRepository:
    """Repository managing chat session persistence and recent message context."""

    def __init__(self, session: Session):
        self.session = session

    def get_or_create_session(
        self,
        session_id: Optional[int] = None,
        user_id: Optional[int] = None,
        title: Optional[str] = "Cuộc trò chuyện mới",
    ) -> int:
        """Find existing session or create a new one, verifying user ownership if authenticated."""
        if session_id:
            row = self.session.execute(
                text("SELECT id, user_id FROM chat_sessions WHERE id = :id"),
                {"id": session_id},
            ).fetchone()
            if row:
                # If session has an owner and authenticated user is different, disallow
                if row.user_id is not None and user_id is not None and row.user_id != user_id:
                    raise PermissionError(f"Session {session_id} does not belong to user {user_id}")
                return row.id

        # Create new session
        result = self.session.execute(
            text("""
                INSERT INTO chat_sessions (user_id, title, created_at, updated_at)
                VALUES (:user_id, :title, :now, :now)
            """),
            {
                "user_id": user_id,
                "title": title or "Cuộc trò chuyện mới",
                "now": datetime.utcnow(),
            },
        )
        self.session.flush()
        # Retrieve the inserted id
        new_id = result.lastrowid
        if not new_id:
            # Fallback for databases like SQLite where lastrowid might need query
            new_id = self.session.execute(
                text("SELECT MAX(id) AS id FROM chat_sessions")
            ).scalar()
        return new_id

    def save_message(
        self,
        session_id: int,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Persist a conversation turn (USER or ASSISTANT) and update session timestamp."""
        now = datetime.utcnow()
        meta_str = json.dumps(metadata) if metadata else None

        result = self.session.execute(
            text("""
                INSERT INTO chat_messages (session_id, role, content, metadata, created_at)
                VALUES (:session_id, :role, :content, :metadata, :now)
            """),
            {
                "session_id": session_id,
                "role": role.upper(),
                "content": content,
                "metadata": meta_str,
                "now": now,
            },
        )
        # Touch session updated_at
        self.session.execute(
            text("UPDATE chat_sessions SET updated_at = :now WHERE id = :id"),
            {"now": now, "id": session_id},
        )
        self.session.flush()
        new_id = result.lastrowid
        if not new_id:
            new_id = self.session.execute(
                text("SELECT MAX(id) AS id FROM chat_messages")
            ).scalar()
        return new_id

    def get_recent_messages(
        self, session_id: int, limit: int = 10
    ) -> List[ChatMessageItem]:
        """Fetch the most recent N messages ordered chronologically."""
        bounded_limit = max(1, min(limit, 20))
        sql = """
            SELECT id, role, content, metadata, created_at
            FROM (
                SELECT id, role, content, metadata, created_at
                FROM chat_messages
                WHERE session_id = :session_id
                ORDER BY created_at DESC, id DESC
                LIMIT :limit
            ) AS recent
            ORDER BY created_at ASC, id ASC
        """
        rows = self.session.execute(
            text(sql), {"session_id": session_id, "limit": bounded_limit}
        ).fetchall()

        messages = []
        for r in rows:
            meta = None
            if r.metadata:
                meta = json.loads(r.metadata) if isinstance(r.metadata, str) else r.metadata
            messages.append(
                ChatMessageItem(
                    id=r.id,
                    role=r.role,
                    content=r.content,
                    created_at=r.created_at,
                    metadata=meta,
                )
            )
        return messages

    def get_session(self, session_id: int, user_id: Optional[int] = None) -> Optional[ChatSessionResponse]:
        """Retrieve session details with message history and ownership check."""
        row = self.session.execute(
            text("SELECT id, user_id, title, created_at FROM chat_sessions WHERE id = :id"),
            {"id": session_id},
        ).fetchone()
        if not row:
            return None
        if row.user_id is not None and user_id is not None and row.user_id != user_id:
            raise PermissionError("Unauthorized access to chat session.")

        messages = self.get_recent_messages(session_id=session_id, limit=50)
        return ChatSessionResponse(
            id=row.id,
            user_id=row.user_id,
            title=row.title,
            created_at=row.created_at,
            messages=messages,
        )
