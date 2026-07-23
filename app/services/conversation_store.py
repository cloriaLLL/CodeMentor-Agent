"""CodeMentor Agent - Conversation storage service.

Manages conversation metadata and message persistence in SQLite.
Supports four conversation types:
1. chat - regular conversations
2. notebook_parent - notebook-level parent with accumulated summary
3. notebook_chapter - notebook chapter linked to parent
4. exercise_module - per language+type exercise generation context
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.database import get_db
from app.core.logger import get_logger

logger = get_logger(__name__)

# Conversation types
TYPE_CHAT = "chat"
TYPE_NOTEBOOK_PARENT = "notebook_parent"
TYPE_NOTEBOOK_CHAPTER = "notebook_chapter"
TYPE_EXERCISE_MODULE = "exercise_module"

# Summary refresh threshold (total new messages across chapters before refreshing)
SUMMARY_REFRESH_THRESHOLD = 6


@dataclass
class Conversation:
    """Conversation metadata record."""
    conversation_id: str
    user_id: str = "default"
    type: str = TYPE_CHAT
    title: str = ""
    parent_id: Optional[str] = None
    module_key: Optional[str] = None
    summary: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    message_count: int = 0
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ConversationMessage:
    """A single message in a conversation."""
    id: int
    conversation_id: str
    role: str
    content: str
    msg_meta: dict[str, Any] = field(default_factory=dict)
    seq: int = 0
    created_at: str = ""


def _row_to_conversation(row) -> Conversation:
    return Conversation(
        conversation_id=row["conversation_id"],
        user_id=row["user_id"],
        type=row["type"],
        title=row["title"] or "",
        parent_id=row["parent_id"],
        module_key=row["module_key"],
        summary=row["summary"] or "",
        meta=json.loads(row["meta"] or "{}"),
        message_count=row["message_count"] or 0,
        created_at=row["created_at"] or "",
        updated_at=row["updated_at"] or "",
    )


def _row_to_message(row) -> ConversationMessage:
    return ConversationMessage(
        id=row["id"],
        conversation_id=row["conversation_id"],
        role=row["role"],
        content=row["content"],
        msg_meta=json.loads(row["msg_meta"] or "{}"),
        seq=row["seq"],
        created_at=row["created_at"] or "",
    )


class ConversationStore:
    """Conversation storage service backed by SQLite."""

    def __init__(self) -> None:
        self.db = get_db()

    # ------------------------------------------------------------------ #
    # Conversation CRUD
    # ------------------------------------------------------------------ #

    def create_conversation(
        self,
        conversation_id: str,
        type: str = TYPE_CHAT,
        title: str = "",
        parent_id: Optional[str] = None,
        module_key: Optional[str] = None,
        meta: Optional[dict[str, Any]] = None,
        user_id: str = "default",
    ) -> Conversation:
        """Create a conversation. Returns existing record if ID already exists (idempotent)."""
        existing = self.get_conversation(conversation_id)
        if existing is not None:
            return existing

        meta_json = json.dumps(meta or {}, ensure_ascii=False)
        self.db.upsert("conversations", {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "type": type,
            "title": title,
            "parent_id": parent_id,
            "module_key": module_key,
            "summary": "",
            "meta": meta_json,
            "message_count": 0,
        }, "conversation_id")
        logger.info("conversation_created", conversation_id=conversation_id, type=type)
        return self.get_conversation(conversation_id)  # type: ignore[return-value]

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation metadata by ID."""
        row = self.db.query_one(
            "SELECT * FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        )
        return _row_to_conversation(row) if row else None

    def get_or_create(
        self,
        conversation_id: str,
        type: str = TYPE_CHAT,
        parent_id: Optional[str] = None,
        module_key: Optional[str] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> Conversation:
        """Get or create a conversation (idempotent)."""
        return self.create_conversation(
            conversation_id=conversation_id,
            type=type,
            parent_id=parent_id,
            module_key=module_key,
            meta=meta,
        )

    def update_conversation(self, conversation_id: str, **updates: Any) -> Optional[Conversation]:
        """Update conversation fields (title, summary, meta, etc.)."""
        conv = self.get_conversation(conversation_id)
        if conv is None:
            return None

        allowed = {"title", "summary", "meta", "message_count"}
        set_clauses: list[str] = []
        params: list[Any] = []

        for key, value in updates.items():
            if key not in allowed:
                continue
            if key == "meta" and isinstance(value, dict):
                new_meta = {**conv.meta, **value}
                value = json.dumps(new_meta, ensure_ascii=False)
            set_clauses.append(f"{key} = ?")
            params.append(value)

        if not set_clauses:
            return conv

        set_clauses.append("updated_at = datetime('now')")
        params.append(conversation_id)
        self.db.execute(
            f"UPDATE conversations SET {', '.join(set_clauses)} WHERE conversation_id = ?",
            tuple(params),
        )
        return self.get_conversation(conversation_id)

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages (cascade)."""
        self.db.execute(
            "DELETE FROM conversation_messages WHERE conversation_id = ?",
            (conversation_id,),
        )
        cur = self.db.execute(
            "DELETE FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        )
        deleted = cur.rowcount > 0
        if deleted:
            logger.info("conversation_deleted", conversation_id=conversation_id)
        return deleted

    # ------------------------------------------------------------------ #
    # Exercise module conversations
    # ------------------------------------------------------------------ #

    def get_or_create_module_conversation(
        self,
        module_key: str,
        meta: Optional[dict[str, Any]] = None,
    ) -> Conversation:
        """Get or create an exercise module conversation by module_key (unique)."""
        row = self.db.query_one(
            "SELECT * FROM conversations WHERE module_key = ?",
            (module_key,),
        )
        if row:
            return _row_to_conversation(row)

        conversation_id = f"mod_{module_key}_{uuid.uuid4().hex[:8]}"
        return self.create_conversation(
            conversation_id=conversation_id,
            type=TYPE_EXERCISE_MODULE,
            title=f"Exercise module: {module_key}",
            module_key=module_key,
            meta=meta,
        )

    def clear_module_conversation(self, module_key: str) -> bool:
        """Clear messages for a module conversation (keep the row, reset count/summary)."""
        conv = self.db.query_one(
            "SELECT conversation_id FROM conversations WHERE module_key = ?",
            (module_key,),
        )
        if conv is None:
            return False

        conv_id = conv["conversation_id"]
        self.db.execute(
            "DELETE FROM conversation_messages WHERE conversation_id = ?",
            (conv_id,),
        )
        self.db.execute(
            "UPDATE conversations SET message_count = 0, summary = '', updated_at = datetime('now') "
            "WHERE conversation_id = ?",
            (conv_id,),
        )
        logger.info("module_conversation_cleared", module_key=module_key)
        return True

    # ------------------------------------------------------------------ #
    # Message CRUD
    # ------------------------------------------------------------------ #

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        msg_meta: Optional[dict[str, Any]] = None,
    ) -> Optional[ConversationMessage]:
        """Append a message to a conversation. Auto-computes seq and increments message_count."""
        conv = self.get_conversation(conversation_id)
        if conv is None:
            logger.warning("add_message: conversation not found", conversation_id=conversation_id)
            return None

        meta_json = json.dumps(msg_meta or {}, ensure_ascii=False)
        # Single-statement insert with seq = MAX(seq)+1 to avoid race condition
        cur = self.db.execute(
            """INSERT INTO conversation_messages (conversation_id, role, content, msg_meta, seq)
               VALUES (?, ?, ?, ?, COALESCE((SELECT MAX(seq) FROM conversation_messages WHERE conversation_id = ?), 0) + 1)""",
            (conversation_id, role, content, meta_json, conversation_id),
        )
        new_seq = cur.lastrowid
        self.db.execute(
            "UPDATE conversations SET message_count = message_count + 1, updated_at = datetime('now') "
            "WHERE conversation_id = ?",
            (conversation_id,),
        )
        if new_seq:
            row = self.db.query_one(
                "SELECT * FROM conversation_messages WHERE id = ?",
                (new_seq,),
            )
            if row:
                return _row_to_message(row)
        return None

    def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConversationMessage]:
        """Get messages ordered by seq ascending."""
        rows = self.db.query_all(
            "SELECT * FROM conversation_messages WHERE conversation_id = ? ORDER BY seq ASC LIMIT ? OFFSET ?",
            (conversation_id, limit, offset),
        )
        return [_row_to_message(r) for r in rows]

    def get_messages_as_llm_history(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> list[dict[str, str]]:
        """Return [{role, content}, ...] for LLM calls (most recent `limit` messages, excluding system)."""
        rows = self.db.query_all(
            "SELECT role, content FROM conversation_messages WHERE conversation_id = ? "
            "ORDER BY seq DESC LIMIT ?",
            (conversation_id, limit),
        )
        # Reverse to chronological order
        rows = list(reversed(rows))
        return [
            {"role": r["role"], "content": r["content"]}
            for r in rows
            if r["role"] in ("user", "assistant") and r["content"]
        ]

    def clear_messages(self, conversation_id: str) -> int:
        """Delete all messages for a conversation. Returns count deleted."""
        cur = self.db.execute(
            "DELETE FROM conversation_messages WHERE conversation_id = ?",
            (conversation_id,),
        )
        self.db.execute(
            "UPDATE conversations SET message_count = 0, updated_at = datetime('now') WHERE conversation_id = ?",
            (conversation_id,),
        )
        return cur.rowcount

    # ------------------------------------------------------------------ #
    # Notebook parent summary
    # ------------------------------------------------------------------ #

    def get_parent_summary(self, parent_conversation_id: str) -> str:
        """Get the summary field of a notebook parent conversation."""
        row = self.db.query_one(
            "SELECT summary FROM conversations WHERE conversation_id = ?",
            (parent_conversation_id,),
        )
        return (row["summary"] or "") if row else ""

    def get_child_chapters(self, parent_conversation_id: str) -> list[Conversation]:
        """Get all chapter conversations under a parent."""
        rows = self.db.query_all(
            "SELECT * FROM conversations WHERE parent_id = ? ORDER BY created_at ASC",
            (parent_conversation_id,),
        )
        return [_row_to_conversation(r) for r in rows]

    def should_refresh_summary(self, parent_conversation_id: str, threshold: int = SUMMARY_REFRESH_THRESHOLD) -> bool:
        """Check if parent summary should be refreshed based on child message count delta."""
        rows = self.db.query_all(
            "SELECT message_count FROM conversations WHERE parent_id = ?",
            (parent_conversation_id,),
        )
        total_child_messages = sum(r["message_count"] or 0 for r in rows)
        # Get the message count at last summary refresh from parent meta
        parent = self.get_conversation(parent_conversation_id)
        if parent is None:
            return False
        last_count = parent.meta.get("last_summary_msg_count", 0)
        return (total_child_messages - last_count) >= threshold

    def refresh_parent_summary(
        self,
        parent_conversation_id: str,
        llm_provider: Any = None,
    ) -> str:
        """Refresh the parent summary by summarizing all child chapter conversations.

        Calls LLM to generate a concise summary. Falls back to simple concatenation if no LLM.
        """
        chapters = self.get_child_chapters(parent_conversation_id)
        if not chapters:
            return ""

        # Build chapter contents from recent messages
        chapter_contents: list[str] = []
        total_messages = 0
        for ch in chapters:
            msgs = self.get_messages_as_llm_history(ch.conversation_id, limit=10)
            if not msgs:
                continue
            total_messages += len(msgs)
            content_lines = [f"## {ch.title or '章节'}\n"]
            for m in msgs:
                role_label = "用户" if m["role"] == "user" else "导师"
                # Truncate long messages
                text = m["content"][:500]
                content_lines.append(f"[{role_label}] {text}\n")
            chapter_contents.append("\n".join(content_lines))

        if not chapter_contents:
            return ""

        combined = "\n\n".join(chapter_contents)

        # Try LLM summarization
        if llm_provider is not None and llm_provider.name != "mock":
            summary = self._llm_summarize(llm_provider, combined)
        else:
            # Fallback: simple truncation
            summary = f"（自动摘要不可用）各章节共 {len(chapters)} 章，累计 {total_messages} 条对话。\n\n" + combined[:500]

        # Store summary and update last_summary_msg_count
        self.update_conversation(
            parent_conversation_id,
            summary=summary,
            meta={"last_summary_msg_count": total_messages},
        )
        logger.info("parent_summary_refreshed", parent_id=parent_conversation_id, summary_len=len(summary))
        return summary

    def _llm_summarize(self, llm_provider: Any, chapter_contents: str) -> str:
        """Call LLM to generate a concise summary of chapter contents."""
        prompt = (
            "请将以下各章节的对话内容整理成一份简洁的学习笔记总结。\n\n"
            "要求:\n"
            "1. 不超过 500 字\n"
            "2. 按章节组织,每章 1-2 句话概括核心知识点\n"
            "3. 标注各章节之间的关联与递进关系\n"
            "4. 适合作为后续章节学习的背景上下文\n\n"
            f"{chapter_contents}\n\n"
            "直接输出总结内容,不要前缀。"
        )
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # We're in an async context but this is a sync method
                # Use asyncio.to_thread to run the async LLM call
                future = asyncio.run_coroutine_threadsafe(
                    llm_provider.chat(
                        system_prompt="你是一位学习笔记整理助手。",
                        user_message=prompt,
                        temperature=0.3,
                        max_tokens=800,
                    ),
                    loop,
                )
                return future.result(timeout=30)
            else:
                return asyncio.run(llm_provider.chat(
                    system_prompt="你是一位学习笔记整理助手。",
                    user_message=prompt,
                    temperature=0.3,
                    max_tokens=800,
                ))
        except Exception as e:
            logger.warning("llm_summarize_failed", error=str(e))
            return f"（摘要生成失败）{chapter_contents[:300]}"
