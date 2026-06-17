import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False, default="assistant")
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False, default="gpt-4o-mini")
    tools: Mapped[list] = mapped_column(JSON, default=list)          # ["web_search", "calculator", ...]
    skills: Mapped[list] = mapped_column(JSON, default=list)         # ["summarization", "code review", ...] — descriptive capability tags injected into system prompt
    channels: Mapped[list] = mapped_column(JSON, default=list)       # ["telegram", "slack"]
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    max_iterations: Mapped[int] = mapped_column(default=10)
    temperature: Mapped[float] = mapped_column(default=0.7)
    guardrails: Mapped[dict] = mapped_column(JSON, default=dict)        # {"max_tokens": 2000, "banned_topics": []}
    schedule: Mapped[dict] = mapped_column(JSON, default=dict)          # {"enabled": true, "cron": "0 9 * * 1-5", "prompt": "..."}
    interaction_rules: Mapped[dict] = mapped_column(JSON, default=dict) # {"response_format": "markdown", "tone": "professional", "custom_instructions": "..."}
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
