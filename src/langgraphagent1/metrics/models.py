from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "task"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    thread: Mapped[str] = mapped_column(Text, nullable=False)

    # хранить удобно объектом:
    # {"planned": ["read_file", ...], "used": ["read_file", "write_file", ...]}
    tools: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # "success" / "error"
    result: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    token_usage: Mapped[list["TokenUsage"]] = relationship(back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_task_created_at", "created_at"),
        Index("ix_task_result", "result"),
    )


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("task.id", ondelete="CASCADE"), nullable=False)
    task: Mapped[Task] = relationship(back_populates="token_usage")

    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    node: Mapped[str] = mapped_column(String(50), nullable=False)   # planner / assistant
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    step: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_token_usage_task_id", "task_id"),
        Index("ix_token_usage_created_at", "created_at"),
        Index("ix_token_usage_task_node_step", "task_id", "node", "step"),
    )
