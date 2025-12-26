from __future__ import annotations

import uuid
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.langgraphagent1.metrics.models import Task, TokenUsage


class TaskDao:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_task(self,
                          task_id: uuid.UUID,
                          name: str,
                          content: str,
                          thread_id: str,) -> None:
        self.session.add(Task(id=task_id, name=name, content=content, thread=thread_id, tools={}, result="success"))

    async def finish_task(self, task_id: uuid.UUID, *, tools: dict, result: str, error: str | None) -> None:
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(tools=tools, result=result, error=error)
        )
        await self.session.execute(stmt)


class TokenUsageDao:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert_many(self, rows: list[TokenUsage]) -> None:
        if rows:
            self.session.add_all(rows)
