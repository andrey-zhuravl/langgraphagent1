from __future__ import annotations
from typing import TypedDict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

ActionType = Literal["say", "tool", "stop"]

class AgentState(TypedDict):
    step: int
    script: list[dict[str, Any]]     # заранее заданные "решения" вместо LLM
    last_action: dict[str, Any] | None
    log: list[str]
    tool_output: Any | None
    error: str | None

def assistant(state: AgentState) -> dict[str, Any]:
    print(f"assistant step: {state['step']}")
    step = state["step"] + 1
    if not state["script"]:
        return {"step": step, "last_action": {"type": "stop"}, "log": state["log"] + ["assistant: script empty -> stop"]}

    action = state["script"].pop(0)
    log = state["log"] + [f"assistant(step={step}): {action}"]
    return {"step": step, "last_action": action, "log": log, "tool_output": None, "error": None, "script": state["script"]}

def run_tool(state: AgentState) -> dict[str, Any]:
    print(f"run_tool step: {state['step']}")
    action = state["last_action"] or {}
    name = action.get("name")
    args = action.get("args", {})

    try:
        if name == "add":
            out = args["a"] + args["b"]
        elif name == "fail_sometimes":
            # имитация флапа/ошибок
            if state["step"] % 2 == 0:
                raise RuntimeError("simulated transient error")
            out = "ok"
        else:
            out = {"unknown_tool": name, "args": args}

        return {"tool_output": out, "log": state["log"] + [f"tool[{name}] -> {out}"], "error": None}

    except Exception as e:
        return {"tool_output": None, "error": str(e), "log": state["log"] + [f"tool[{name}] ERROR: {e}"]}

def route_after_assistant(state: AgentState) -> str:
    print(f"route_after_assistant step: {state['step']}")
    a = state["last_action"] or {}
    t = a.get("type")
    if t == "tool":
        return "run_tool"
    if t == "stop":
        return END
    return "assistant"

def run_graph() -> dict[str, Any]:
    builder = StateGraph(AgentState)
    builder.add_node("assistant", assistant)
    builder.add_node("assistant2", assistant)
    builder.add_node("run_tool", run_tool)
    builder.add_edge(START, "assistant")
    builder.add_edge("assistant", "assistant1")
    builder.add_conditional_edges("assistant", route_after_assistant, {"run_tool": "run_tool", "assistant": "assistant", END: END})
    builder.add_conditional_edges("assistant", route_after_assistant, {"run_tool": "run_tool", "assistant": "assistant", END: END})
    builder.add_edge("run_tool", "assistant")

    graph = builder.compile(checkpointer=InMemorySaver())

    initial: AgentState = {
        "step": 0,
        "script": [
            {"type": "say", "text": "hi"},
            {"type": "tool", "name": "add", "args": {"a": 2, "b": 3}},
            {"type": "tool", "name": "fail_sometimes", "args": {}},
            {"type": "stop"},
        ],
        "last_action": None,
        "log": [],
        "tool_output": None,
        "error": None,
    }
    config = {"configurable": {"thread_id": "dev-thread"}}
    result = graph.invoke(initial, config = config)
    print("\n".join(result["log"]))
    print("tool_output:", result["tool_output"], "error:", result["error"])
    return result

def main() -> int:
    out = run_graph()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
