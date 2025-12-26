from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from src.langgraphagent1 import filesystem_utils
from src.langgraphagent1.metrics.extract import extract_token_usage, extract_tokens
from src.langgraphagent1.metrics.service import MetricsService
from src.langgraphagent1.plan_parser import plan_parse
from src.langgraphagent1.prompts.plan_prompt import get_plan_prompt
from src.langgraphagent1.state import AgentState
from src.langgraphagent1.utils import safe_invoke

metrics = MetricsService()

def create_planner_node(llm: ChatOpenAI,
                        tools_names_text: str,
                        debug_dir: str = "debug"):
    def planner(state: AgentState) -> AgentState:
        memory_summary = state.get("memory_summary", "") or ""
        user_message = state["messages"][-1].content  # исходный запрос пользователя

        system_prompt = SystemMessage(content=get_plan_prompt(memory_summary, tools_names_text)
                                      .format(memory_summary=memory_summary))
        filesystem_utils.write_file(debug_dir, "prompt_0plan.txt", str(user_message) + "\n==\n" + str(system_prompt))

        # Вызываем LLM только с системным промптом и исходным запросом пользователя
        response = safe_invoke(llm, [system_prompt, HumanMessage(content=user_message)])

        event = extract_tokens(ai_message = response, node="planer", step=0, llm=llm,)

        raw_content = response.content.strip()
        filesystem_utils.write_file(debug_dir, "llm_0plan.txt", str(raw_content))
        plan_list = plan_parse(raw_content)

        steps = [step["step"] for step in plan_list]
        tools = [step["tool"] for step in plan_list]

        # Важно: возвращаем полный dict с новым планом
        return {
            "llm_usage_events": [event],
            "plan": steps,
            "tools": tools,
            "current_step": 0,
            "llm_calls": 1,
            "steps": 1,
        }

    return planner
