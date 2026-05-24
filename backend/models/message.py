import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(String(36), nullable=True)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)          # telegram | slack | internal
    channel_user_id: Mapped[str] = mapped_column(String(100), default="")
    channel_chat_id: Mapped[str] = mapped_column(String(100), default="")
    direction: Mapped[str] = mapped_column(String(10), nullable=False)        # inbound | outbound
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
