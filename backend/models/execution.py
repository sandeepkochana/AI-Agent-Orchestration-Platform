import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id: Mapped[str] = mapped_column(String(36), nullable=True)
    agent_id: Mapped[str] = mapped_column(String(36), nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(30), default="manual")  # manual | schedule | channel
    input_message: Mapped[str] = mapped_column(Text, default="")
    output_message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | running | completed | failed
    total_tokens: Mapped[int] = mapped_column(default=0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id: Mapped[str] = mapped_column(String(36), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(36), nullable=True)
    agent_name: Mapped[str] = mapped_column(String(100), default="")
    log_type: Mapped[str] = mapped_column(String(30), default="message")  # message | tool_call | tool_result | error
    content: Mapped[str] = mapped_column(Text, default="")
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
