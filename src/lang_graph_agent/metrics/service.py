from __future__ import annotations

import uuid
from typing import Any

from src.lang_graph_agent.metrics.dao import TaskDao, TokenUsageDao
from src.lang_graph_agent.metrics.db import SESSION_FACTORY
from src.lang_graph_agent.metrics.models import TokenUsage


class MetricsService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    async def create_task(self, *,
                          task_id: uuid.UUID,
                          name: str,
                          content: str,
                          thread_id: str,) -> None:
        async with SESSION_FACTORY() as session:
            dao = TaskDao(session)
            await dao.create_task(task_id, name, content, thread_id)
            await session.commit()

    async def create_token_usage(self, *,
                          task_id: uuid.UUID,
                          name: str,
                          content: str,
                          thread_id: str,) -> None:
        async with SESSION_FACTORY() as session:
            dao = TaskDao(session)
            await dao.create_task(task_id, name, content, thread_id)
            await session.commit()

    async def finalize_task_and_save_usage(
        self,
        *,
        task_id: uuid.UUID,
        planned_tools: list[str],
        used_tools: list[str],
        usage_events: list[dict[str, Any]],
        success: bool,
        error: str | None,
    ) -> None:
        tools_obj = {"planned": planned_tools, "used": used_tools}
        result = "success" if success else "error"

        token_rows: list[TokenUsage] = []
        for e in usage_events:
            token_rows.append(
                TokenUsage(
                    task_id=task_id,
                    prompt_tokens=e.get("prompt_tokens"),
                    completion_tokens=e.get("completion_tokens"),
                    total_tokens=e.get("total_tokens"),
                    node=e.get("node", "unknown"),
                    model=e.get("model"),
                    step=e.get("step"),
                )
            )

        async with SESSION_FACTORY() as session:
            task_dao = TaskDao(session)
            usage_dao = TokenUsageDao(session)

            await task_dao.finish_task(task_id, tools=tools_obj, result=result, error=error)
            await usage_dao.insert_many(token_rows)

            await session.commit()
