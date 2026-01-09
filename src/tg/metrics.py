import uuid

from src.lang_graph_agent.metrics.service import MetricsService

metrics = MetricsService()


async def create_agent_task(name: str, content: str, thread_id: str) -> str:
    task_id = uuid.uuid4()
    await metrics.create_task(task_id=task_id, name=name, content=content, thread_id=thread_id)
    return task_id


async def finalize_task_and_usage(result, task_id: str) -> None:
    planned = result.get("tools", []) or []  # planner возвращает tools:contentReference[oaicite:6]{index=6}
    used = result.get("tools_used", []) or []
    events = result.get("llm_usage_events", []) or []

    await metrics.finalize_task_and_save_usage(
        task_id=task_id,
        planned_tools=planned,
        used_tools=used,
        usage_events=events,
        success=True,
        error=None,
    )
