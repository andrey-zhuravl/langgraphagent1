from __future__ import annotations

from typing import Any
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from src.langgraphagent1 import filesystem_utils
from src.langgraphagent1.mcp_tool.mcp_bridge import (
    render_tools_for_prompt, )
from src.langgraphagent1.metrics.extract import extract_tokens
from src.langgraphagent1.prompts.assistant_prompt import get_assistant_prompt, get_assistant_prompt_final
from src.langgraphagent1.settings import Settings
from src.langgraphagent1.state import AgentState
from src.langgraphagent1.utils import safe_invoke


def create_assistant_node(llm: ChatOpenAI,
                          s: Settings,
                          mcp_tools: list[Any],
                          debug_dir: str = "debug"):
    def assistant(state: AgentState) -> AgentState:
        steps = int(state.get("current_step", 1))

        # Если дошли до лимита — не возвращаем STOP наружу,
        # а заставляем модель выдать FINAL.
        if steps >= s.max_steps:
            force = SystemMessage(
                content=(
                    "Ты достиг лимита шагов. НЕМЕДЛЕННО верни ответ строго одной строкой:\n"
                    "FINAL: <ответ>\n"
                    "Запрещено использовать TOOL."
                )
            )
            final_resp = safe_invoke(llm, [force] + state["messages"][-20:])
            event = extract_tokens(ai_message=final_resp, node="assistant", step=steps + 1, llm=llm, )

            if s.debug:
                print("[assistant FORCE_FINAL]", final_resp.content)
            return {
                "llm_usage_events": [event],
                "messages": [final_resp],
                "current_step": steps + 1,
                "llm_calls": int(state.get("llm_calls", 0)) + 1,
                "steps": steps + 1,
            }
        current_step_number = state["current_step"]
        if current_step_number < len(state["plan"]):
            current_step_str = state["plan"][current_step_number]
            current_tool_str = state["tools"][current_step_number]
            current_tool = None
            for t in mcp_tools:
                if t.name == current_tool_str:
                    current_tool = t
            full_tool_text = render_tools_for_prompt([current_tool])
            content = get_assistant_prompt(state["general_task"], current_step_str, full_tool_text)
        else:
            current_step_str = "FINAL"
            content = get_assistant_prompt_final(state["general_task"], current_step_str)

        print()
        filesystem_utils.write_file(debug_dir, f"prompt_{steps}.txt", str(state["messages"]) + "\n==\n" + str(content))
        system = SystemMessage(
            content=content
        )

        response = safe_invoke(llm, [system] + state["messages"])
        event = extract_tokens(ai_message=response, node="assistant", step=steps + 1, llm=llm, )
        print(f"ОТВЕТ - {response}")
        filesystem_utils.write_file(debug_dir, f"llm_{steps}.txt", response.content)
        if s.debug:
            print("[assistant]", response.content)
        return {
            "llm_usage_events": [event],
            "messages": [response],
            "current_step": steps + 1,
            "llm_calls": int(state.get("llm_calls", 0)) + 1,
            "steps": steps + 1,
        }

    return assistant
