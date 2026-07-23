"""CodeMentor Agent - Learning state management service.

Manages learning sessions, progress tracking, and teaching phase transitions.
Implements the three-layer teaching structure state machine:
  conversation -> teaching (4 steps) -> progression -> [next | review | pause]
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from app.core.database import get_db
from app.core.logger import get_logger

logger = get_logger(__name__)

# Teaching phases
PHASE_CONVERSATION = "conversation"
PHASE_TEACHING = "teaching"
PHASE_PROGRESSION = "progression"
PHASE_COMPLETED = "completed"

# Teaching steps within PHASE_TEACHING
STEP_OVERVIEW = 0      # Not started yet (shouldn't happen in teaching)
STEP_EXAMPLE = 1       # 实例先行
STEP_CONCEPT = 2       # 概念跟进
STEP_TRACING = 3       # 溯源深化
STEP_EXERCISE = 4      # 练习巩固

STEP_NAMES = {
    1: "实例先行",
    2: "概念跟进",
    3: "溯源深化",
    4: "练习巩固",
}

# Progress statuses
STATUS_NOT_STARTED = "not_started"
STATUS_LEARNING = "learning"
STATUS_PRACTICED = "practiced"
STATUS_MASTERED = "mastered"


class LearningSession:
    """Represents a learning session state."""

    def __init__(
        self,
        session_id: str,
        user_id: str = "default",
        topic: str = "",
        phase: str = PHASE_CONVERSATION,
        teaching_step: int = 0,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.session_id = session_id
        self.user_id = user_id
        self.topic = topic
        self.phase = phase
        self.teaching_step = teaching_step
        self.context = context or {}

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "topic": self.topic,
            "phase": self.phase,
            "teaching_step": self.teaching_step,
            "context": self.context,
        }


class LearningStateService:
    """Service for managing learning sessions and progress."""

    def __init__(self) -> None:
        self.db = get_db()

    # ------------------------------------------------------------------ #
    # Session management
    # ------------------------------------------------------------------ #

    def create_session(self, topic: str, user_id: str = "default") -> LearningSession:
        """Create a new learning session (Layer 1: conversation starts)."""
        session_id = uuid.uuid4().hex[:12]
        session = LearningSession(
            session_id=session_id,
            user_id=user_id,
            topic=topic,
            phase=PHASE_CONVERSATION,
            teaching_step=0,
            context={},
        )
        self.db.upsert("learning_sessions", {
            "session_id": session_id,
            "user_id": user_id,
            "topic": topic,
            "phase": PHASE_CONVERSATION,
            "teaching_step": 0,
            "context": "{}",
        }, "session_id")
        logger.info("session_created", session_id=session_id, topic=topic)
        return session

    def get_session(self, session_id: str) -> Optional[LearningSession]:
        """Get session by ID."""
        row = self.db.query_one(
            "SELECT * FROM learning_sessions WHERE session_id = ?",
            (session_id,),
        )
        if row is None:
            return None
        return LearningSession(
            session_id=row["session_id"],
            user_id=row["user_id"],
            topic=row["topic"],
            phase=row["phase"],
            teaching_step=row["teaching_step"],
            context=json.loads(row["context"] or "{}"),
        )

    def update_session(self, session_id: str, **updates: Any) -> Optional[LearningSession]:
        """Update session fields."""
        session = self.get_session(session_id)
        if session is None:
            return None

        if "phase" in updates:
            session.phase = updates["phase"]
        if "teaching_step" in updates:
            session.teaching_step = updates["teaching_step"]
        if "context" in updates:
            session.context.update(updates["context"])

        self.db.execute(
            "UPDATE learning_sessions SET phase = ?, teaching_step = ?, context = ?, updated_at = datetime('now') WHERE session_id = ?",
            (session.phase, session.teaching_step, json.dumps(session.context, ensure_ascii=False), session_id),
        )
        return session

    def advance_teaching_step(self, session_id: str) -> Optional[LearningSession]:
        """Advance to the next teaching step (Layer 2: teaching rhythm)."""
        session = self.get_session(session_id)
        if session is None:
            return None
        if session.phase != PHASE_TEACHING:
            return session
        if session.teaching_step < STEP_EXERCISE:
            session.teaching_step += 1
            self.update_session(session_id, teaching_step=session.teaching_step)
            logger.info("teaching_step_advanced", session_id=session_id, step=session.teaching_step)
        if session.teaching_step >= STEP_EXERCISE:
            self.update_session(session_id, phase=PHASE_PROGRESSION)
        return session

    def start_teaching(self, session_id: str) -> Optional[LearningSession]:
        """Transition from conversation to teaching phase."""
        return self.update_session(
            session_id,
            phase=PHASE_TEACHING,
            teaching_step=STEP_EXAMPLE,
        )

    def complete_knowledge_point(self, session_id: str, knowledge_point: str, score: int = 0) -> None:
        """Mark a knowledge point as completed (Layer 3: progression)."""
        status = STATUS_MASTERED if score >= 80 else STATUS_PRACTICED
        self.db.execute(
            """INSERT INTO learning_progress (session_id, knowledge_point, status, mastery_score, attempts, updated_at)
               VALUES (?, ?, ?, ?, 1, datetime('now'))
               ON CONFLICT(id) DO UPDATE SET status=excluded.status, mastery_score=excluded.mastery_score, updated_at=datetime('now')
            """,
            (session_id, knowledge_point, status, score),
        )
        self.update_session(session_id, phase=PHASE_PROGRESSION)

    # ------------------------------------------------------------------ #
    # Progress tracking
    # ------------------------------------------------------------------ #

    def get_progress(self, session_id: str) -> list[dict]:
        """Get all learning progress for a session."""
        rows = self.db.query_all(
            "SELECT * FROM learning_progress WHERE session_id = ? ORDER BY updated_at DESC",
            (session_id,),
        )
        return [dict(r) for r in rows]

    def get_mastery_score(self, session_id: str, knowledge_point: str) -> int:
        """Get mastery score for a specific knowledge point."""
        row = self.db.query_one(
            "SELECT mastery_score FROM learning_progress WHERE session_id = ? AND knowledge_point = ?",
            (session_id, knowledge_point),
        )
        return row["mastery_score"] if row else 0

    # ------------------------------------------------------------------ #
    # Exercise submission tracking
    # ------------------------------------------------------------------ #

    def record_submission(
        self,
        session_id: str,
        exercise_id: str,
        exercise_type: str,
        user_answer: str,
        result: str,
        score: int = 0,
        feedback: str = "",
        exercise_subtype: str = "",
    ) -> int:
        """Record an exercise submission."""
        cur = self.db.execute(
            """INSERT INTO exercise_submissions
               (session_id, exercise_id, exercise_type, exercise_subtype, user_answer, result, score, feedback)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, exercise_id, exercise_type, exercise_subtype, user_answer, result, score, feedback),
        )
        return cur.lastrowid or 0

    def get_submissions(self, session_id: str) -> list[dict]:
        """Get all submissions for a session."""
        rows = self.db.query_all(
            "SELECT * FROM exercise_submissions WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
        )
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Session context helpers
    # ------------------------------------------------------------------ #

    def add_context(self, session_id: str, key: str, value: Any) -> None:
        """Add a key-value pair to session context."""
        session = self.get_session(session_id)
        if session:
            session.context[key] = value
            self.update_session(session_id, context=session.context)

    def get_context(self, session_id: str, key: str, default: Any = None) -> Any:
        """Get a value from session context."""
        session = self.get_session(session_id)
        if session:
            return session.context.get(key, default)
        return default
