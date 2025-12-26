from __future__ import annotations

from langgraph.graph import END

from src.langgraphagent1.state import AgentState


def create_route_after_assistant_node():
    def route_after_assistant(state: AgentState) -> str:
        text = (state["messages"][-1].content or "").strip()
        return "run_tool" if "TOOL:" in text else END
    return route_after_assistant