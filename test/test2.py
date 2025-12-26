from __future__ import annotations

from typing import TypedDict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.typing import StateT, ContextT, InputT, OutputT

from src.visual.to_png import save_langgraph_png2

ActionType = Literal["tool", "human", "stop"]
TaskStatus = Literal["pending", "running", "done", "retry", "failed", "blocked"]


class Task(TypedDict):
    id: str
    kind: str                 # "add" | "factorial" | "flaky"
    args: dict[str, Any]
    expected: Any | None      # для критика
    needs_human: bool


class AgentState(TypedDict):
    step: int
    plan: list[Task]                  # очередь задач
    current: Task | None              # текущая задача
    status: dict[str, TaskStatus]     # статус по task.id
    attempts: dict[str, int]          # ретраи по task.id
    max_retries: int

    last_action: dict[str, Any] | None
    tool_output: Any | None
    error: str | None

    # “человек-в-петле” на заглушках:
    human_inbox: dict[str, str]       # task.id -> "approve"|"reject"
    results: dict[str, Any]           # task.id -> результат
    log: list[str]


# -------------------- Узлы --------------------

def validate_state(state: AgentState) -> dict[str, Any]:
    # маленький “инвариант” чтобы ловить сломанные стейты
    required = ["step", "plan", "status", "attempts", "max_retries", "human_inbox", "results", "log"]
    missing = [k for k in required if k not in state]
    if missing:
        return {"error": f"STATE_INVARIANT_BROKEN missing={missing}", "log": state.get("log", []) + [f"validate: missing {missing}"]}
    return {"error": None}


def planner(state: AgentState) -> dict[str, Any]:
    # если плана нет — создаём
    if state["plan"]:
        return {"log": state["log"] + ["planner: plan already exists"]}

    plan: list[Task] = [
        {"id": "t1", "kind": "add",       "args": {"a": 2, "b": 3}, "expected": 5,   "needs_human": False},
        {"id": "t2", "kind": "factorial", "args": {"n": 6},         "expected": 720, "needs_human": True},  # потребуем апрув
        {"id": "t3", "kind": "flaky",     "args": {},               "expected": "ok","needs_human": False},
    ]
    status = {t["id"]: "pending" for t in plan}
    attempts = {t["id"]: 0 for t in plan}

    return {
        "plan": plan,
        "status": status,
        "attempts": attempts,
        "log": state["log"] + [f"planner: created {len(plan)} tasks"]
    }


def executor(state: AgentState) -> dict[str, Any]:
    step = state["step"] + 1

    # взять следующую pending задачу
    current = None
    for t in state["plan"]:
        if state["status"].get(t["id"]) == "pending":
            current = t
            break

    if current is None:
        return {
            "step": step,
            "last_action": {"type": "stop"},
            "current": None,
            "log": state["log"] + [f"executor(step={step}): no pending tasks -> stop"]
        }

    # human gate перед выполнением, если надо
    if current["needs_human"]:
        return {
            "step": step,
            "current": current,
            "status": {**state["status"], current["id"]: "blocked"},
            "last_action": {"type": "human", "task_id": current["id"]},
            "log": state["log"] + [f"executor(step={step}): task {current['id']} needs human approval"]
        }

    return {
        "step": step,
        "current": current,
        "status": {**state["status"], current["id"]: "running"},
        "last_action": {"type": "tool", "name": current["kind"], "args": current["args"], "task_id": current["id"]},
        "log": state["log"] + [f"executor(step={step}): run tool for task {current['id']} ({current['kind']})"]
    }


def human_gate(state: AgentState) -> dict[str, Any]:
    current = state["current"]
    if not current:
        return {"error": "human_gate: no current task"}

    tid = current["id"]
    decision = state["human_inbox"].get(tid)  # "approve" or "reject" or None

    if decision == "approve":
        return {
            "status": {**state["status"], tid: "running"},
            "last_action": {"type": "tool", "name": current["kind"], "args": current["args"], "task_id": tid},
            "log": state["log"] + [f"human_gate: APPROVED task {tid} -> continue"]
        }

    if decision == "reject":
        return {
            "status": {**state["status"], tid: "failed"},
            "results": {**state["results"], tid: {"blocked": True, "reason": "human_reject"}},
            "last_action": {"type": "stop"},
            "log": state["log"] + [f"human_gate: REJECTED task {tid} -> fail task"]
        }

    # нет решения -> остаёмся заблокированными (в демо просто завершим)
    return {
        "status": {**state["status"], tid: "blocked"},
        "last_action": {"type": "stop"},
        "log": state["log"] + [f"human_gate: no decision for {tid} -> stop (demo)"]
    }


def run_tool(state: AgentState) -> dict[str, Any]:
    a = state["last_action"] or {}
    tid = a.get("task_id")
    name = a.get("name")
    args = a.get("args", {})

    # инкремент попыток
    attempts = dict(state["attempts"])
    if tid:
        attempts[tid] = attempts.get(tid, 0) + 1

    try:
        if name == "add":
            out = args["a"] + args["b"]

        elif name == "factorial":
            n = args["n"]
            out = 1
            for i in range(2, n + 1):
                out *= i

        elif name == "flaky":
            # детерминированный “флап” по номеру попытки:
            # первая попытка падает, вторая — ок
            if attempts[tid] == 1:
                raise RuntimeError("simulated transient error")
            out = "ok"

        else:
            out = {"unknown_tool": name, "args": args}

        return {
            "attempts": attempts,
            "tool_output": out,
            "error": None,
            "log": state["log"] + [f"tool[{name}] (attempt={attempts.get(tid)}) -> {out}"]
        }

    except Exception as e:
        return {
            "attempts": attempts,
            "tool_output": None,
            "error": str(e),
            "log": state["log"] + [f"tool[{name}] (attempt={attempts.get(tid)}) ERROR: {e}"]
        }


def critic(state: AgentState) -> dict[str, Any]:
    current = state["current"]
    if not current:
        return {"error": "critic: no current task"}

    tid = current["id"]
    expected = current["expected"]
    attempt = state["attempts"].get(tid, 0)

    # если инструмент упал — решаем retry/fail
    if state["error"]:
        if attempt <= state["max_retries"]:
            return {
                "status": {**state["status"], tid: "retry"},
                "log": state["log"] + [f"critic: tool error, will retry task {tid} (attempt={attempt})"]
            }
        return {
            "status": {**state["status"], tid: "failed"},
            "results": {**state["results"], tid: {"error": state["error"]}},
            "log": state["log"] + [f"critic: tool error, retries exceeded -> FAIL task {tid}"]
        }

    # проверка ожиданий (для демо)
    out = state["tool_output"]
    if expected is not None and out != expected:
        return {
            "status": {**state["status"], tid: "failed"},
            "results": {**state["results"], tid: {"bad_output": out, "expected": expected}},
            "log": state["log"] + [f"critic: mismatch -> FAIL task {tid} (out={out}, expected={expected})"]
        }

    return {
        "status": {**state["status"], tid: "done"},
        "results": {**state["results"], tid: out},
        "log": state["log"] + [f"critic: OK -> DONE task {tid}"]
    }


def mark_retry_as_running(state: AgentState) -> dict[str, Any]:
    current = state["current"]
    if not current:
        return {"error": "retry: no current task"}
    tid = current["id"]
    return {
        "status": {**state["status"], tid: "running"},
        "last_action": {"type": "tool", "name": current["kind"], "args": current["args"], "task_id": tid},
        "log": state["log"] + [f"retry: re-run tool for task {tid}"]
    }


# -------------------- Роутинг --------------------

def route_after_executor(state: AgentState) -> str:
    a = state["last_action"] or {}
    t = a.get("type")
    if t == "tool":
        return "run_tool"
    if t == "human":
        return "human_gate"
    return END

def route_after_critic(state: AgentState) -> str:
    current = state["current"]
    if not current:
        return END
    tid = current["id"]
    st = state["status"].get(tid)
    if st == "retry":
        return "retry"
    # done/failed -> идём к executor за следующей задачей
    return "executor"


# -------------------- Сборка графа --------------------

def build() -> CompiledStateGraph[StateT, ContextT, InputT, OutputT]:
    builder = StateGraph(AgentState)

    builder.add_node("validate", validate_state)
    builder.add_node("planner", planner)
    builder.add_node("executor", executor)
    builder.add_node("human_gate", human_gate)
    builder.add_node("human_gate1", human_gate)
    builder.add_node("run_tool", run_tool)
    builder.add_node("critic", critic)
    builder.add_node("retry", mark_retry_as_running)

    builder.add_edge(START, "validate")
    builder.add_edge("validate", "planner")
    builder.add_edge("planner", "executor")

    builder.add_conditional_edges("executor", route_after_executor, {
        "run_tool": "run_tool",
        "human_gate": "human_gate",
        END: END
    })

    builder.add_edge("human_gate", "executor")   # после human_gate executor снова решит что делать (или stop)

    builder.add_edge("run_tool", "critic")

    builder.add_conditional_edges("critic", route_after_critic, {
        "retry": "retry",
        "executor": "executor"
    })

    builder.add_edge("retry", "run_tool")

    graph = builder.compile(checkpointer=InMemorySaver())
    return graph


# -------------------- Запуск демо --------------------

def run_graph(graph: CompiledStateGraph[StateT, ContextT, InputT, OutputT]):
    initial: AgentState = {
        "step": 0,
        "plan": [],
        "current": None,
        "status": {},
        "attempts": {},
        "max_retries": 2,

        "last_action": None,
        "tool_output": None,
        "error": None,

        # заранее “ответ человека”
        "human_inbox": {"t2": "approve"},
        "results": {},
        "log": [],
    }

    # (опционально) с thread_id — чтобы поиграться с чекпойнтами/резюмами
    cfg = {"configurable": {"thread_id": "demo-thread"}}

    final_state = graph.invoke(initial, config=cfg)

    print("\n".join(final_state["log"]))
    print("STATUS:", final_state["status"])
    print("RESULTS:", final_state["results"])
    print("ATTEMPTS:", final_state["attempts"])

def main() -> int:
    graph = build()
    save_langgraph_png2(graph, "graph.png")
    out = run_graph(graph=graph)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())