from __future__ import annotations

import json
from langchain_core.messages import SystemMessage
from langgraph.graph import END
from src.langgraphagent1.settings import Settings
from src.langgraphagent1.state import AgentState
from src.langgraphagent1.utils import safe_call_tool

def parse_tool_calls(text: str) -> list[dict]:
    lines = (text or "").splitlines()

    calls = []
    cur = None
    cur_key = None
    buf = []

    def flush_arg():
        nonlocal cur_key, buf, cur
        if cur and cur_key is not None:
            cur["args"][cur_key] = "\n".join(buf).rstrip()
        cur_key = None
        buf = []

    def flush_call():
        nonlocal cur
        if cur:
            flush_arg()
            calls.append(cur)
        cur = None

    for raw in lines:
        s = raw.strip()

        if s.startswith("FINAL:"):
            break

        if s.startswith("TOOL:") or s.startswith("TOOL="):
            flush_call()
            payload = json.loads(s[len("TOOL:"):].strip())
            cur = {"name": payload["name"], "args": dict(payload.get("args") or {})}
            continue

        if s.startswith("TOOL_ARG=") or s.startswith("TOOL_ARG:"):
            if not cur:
                raise ValueError("TOOL_ARG before TOOL")
            flush_arg()
            rest = s[len("TOOL_ARG="):]
            p = rest.find(":")
            if p < 0:
                raise ValueError("Bad TOOL_ARG header")
            cur_key = rest[:p].strip()
            inline = rest[p + 1:].lstrip()
            if inline:
                buf.append(inline)
            continue

        if cur_key is not None:
            buf.append(raw.rstrip("\r\n"))

    flush_call()
    return calls


def route_after_assistant(state: AgentState) -> str:
    text = (state["messages"][-1].content or "").strip()
    return "run_tool" if "TOOL:" in text else END


def create_tool_runner_node(s: Settings, mcp_tool_names: set):
    async def run_tool(state: AgentState) -> AgentState:
        raw = (state["messages"][-1].content or "").strip()
        try:
            calls = parse_tool_calls(raw)
            if not calls:
                raise ValueError("No TOOL blocks")
            results = []
            for c in calls:
                name = c["name"]
                args = c["args"]

                if name not in mcp_tool_names:
                    raise ValueError(f"Tool not allowed: {name}")

                # if name == "write_file":
                #     args = _adapt_write_file_args(args)

                r = await safe_call_tool(name, args)
                results.append({name: r})

            names = [c["name"] for c in calls]
            tools_used = state.get("tools_used", [])
            tools_used = list(set(tools_used + names))
            return {
                "tools_used": tools_used,
                "messages": [SystemMessage(content="TOOL_RESULT_BATCH: " + json.dumps(results, ensure_ascii=False))],
                "llm_calls": int(state.get("llm_calls", 0)),
                "steps": int(state.get("steps", 0)),
            }
        except Exception as e:
            if s.debug:
                print("[run_tool ERROR]", e)
            return {
                "messages": [
                    SystemMessage(
                        content=(
                            f"TOOL_ERROR: {e}\n"
                            'Повтори строго:'
                            'TOOL: {"name":"<tool_name>"}\n\n'
                            "TOOL_ARG=<название arg1>:\n"
                            "<значение arg1>\n"
                            "TOOL_ARG=<название arg2>:\n"
                            "<значение arg2>\n"
                        )
                    )
                ],
                "llm_calls": int(state.get("llm_calls", 0)),
                "steps": int(state.get("steps", 0)),
            }

    return run_tool
