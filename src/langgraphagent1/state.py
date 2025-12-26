from __future__ import annotations

import operator
import os

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict, Annotated

load_dotenv()
redis_url: str = os.environ.get("REDIS_URL")
DIR_DEBUG: str = 'debug'


class AgentState(TypedDict):
    task_id: str
    llm_usage_events: Annotated[list[dict], operator.add]
    tools_used: Annotated[list[str], operator.add]
    general_task: str
    messages: Annotated[list[BaseMessage], operator.add]
    plan: list[str]  # План шагов
    tools: list[str]
    current_step: int = 0
    memory_summary: str | None  # Краткий саммари прошлых взаимодействий
    steps: int
    llm_calls: int
