from dataclasses import dataclass
from datetime import datetime, timezone

from src.langgraphagent1.agent import run_once
from src.langgraphagent1.metrics.service import MetricsService
from src.tg.metrics import create_agent_task, finalize_task_and_usage

metrics = MetricsService()


@dataclass
class AgentResponse:
    text: str


step = 1


async def call_agent(text: str, thread_id: str, meta: dict) -> AgentResponse:
    global step
    time = datetime.now(timezone.utc).isoformat()
    debug_dir = f"task_{time[:19].replace(':', '-')}_{step}"
    task_id = await create_agent_task(name=text, content=text, thread_id=thread_id)

    result = await run_once(text,
                            debug_dir=debug_dir,
                            thread_id=thread_id,
                            task_id=task_id)

    await finalize_task_and_usage(result, task_id)

    answer = result["messages"][-1]
    answer_text = (getattr(answer, "content", "") or "").strip()
    if answer_text.startswith("FINAL:"):
        answer_text = answer_text[len("FINAL:"):]
    print(f"call_agent = {text}")
    step = step + 1
    return AgentResponse(text=f"{answer_text}")
