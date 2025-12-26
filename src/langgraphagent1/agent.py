from __future__ import annotations

import os
from dataclasses import dataclass
from typing_extensions import TypedDict, Annotated
import operator

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver


class AgentState(TypedDict):
    # messages-as-state: это главный “позвоночник” всей системы
    messages: Annotated[list[BaseMessage], operator.add]
    llm_calls: int


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.2


def load_settings() -> Settings:
    base_url = os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1")
    api_key = os.environ.get("OPENAI_API_KEY", "local-key")
    model = os.environ.get("OPENAI_MODEL", "local-model")
    return Settings(base_url=base_url, api_key=api_key, model=model)


def build_graph() -> callable:
    s = load_settings()

    llm = ChatOpenAI(
        model=s.model,
        base_url=s.base_url,
        api_key=s.api_key,
        temperature=s.temperature,
    )

    def llm_call(state: AgentState) -> AgentState:
        system = SystemMessage(
            content=(
                "Ты — LangGraphAgent1 (минимальный прототип). "
                "Отвечай кратко и по делу."
            )
        )
        # ВАЖНО: messages должны быть BaseMessage-объектами
        response = llm.invoke([system] + state["messages"])

        return {
            "messages": [response],
            "llm_calls": int(state.get("llm_calls", 0)) + 1,
        }

    builder = StateGraph(AgentState)
    builder.add_node("llm_call", llm_call)
    builder.add_edge(START, "llm_call")
    builder.add_edge("llm_call", END)

    # checkpointer нужен уже сейчас — дальше он потребуется для interrupt()/HITL
    checkpointer = InMemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    return graph


def run_once(user_text: str, *, thread_id: str = "dev-thread") -> dict:
    graph = build_graph()
    init_state: AgentState = {
        "messages": [HumanMessage(content=user_text)],
        "llm_calls": 0,
    }

    # thread_id — это “указатель” на сохранённое состояние (понадобится для HITL)
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke(init_state, config=config)
