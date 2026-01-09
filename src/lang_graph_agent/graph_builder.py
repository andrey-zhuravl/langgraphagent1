from __future__ import annotations

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from src.lang_graph_agent.conditional_edges.route_after_assistant import create_route_after_assistant_node
from src.lang_graph_agent.mcp_tool.mcp_bridge import (
    render_tools_for_prompt,
    render_tools_name_for_prompt,
    safe_list_tools,
)
from src.lang_graph_agent.nodes.assistant import create_assistant_node
from src.lang_graph_agent.nodes.planer import create_planner_node
from src.lang_graph_agent.nodes.tool_runner import create_tool_runner_node
from src.lang_graph_agent.settings import load_settings, _parse_allowed
from src.lang_graph_agent.state import AgentState

async def build_graph(debug_dir: str, checkpointer) -> callable:
    s = load_settings()
    allowed = _parse_allowed(s.mcp_allowed_tools_csv)

    mcp_tools_all = await safe_list_tools()
    mcp_tools = list(mcp_tools_all)

    mcp_tool_names = {t.name for t in mcp_tools}
    tools_text = render_tools_for_prompt(mcp_tools)
    tools_names_text = render_tools_name_for_prompt(mcp_tools)

    if s.debug:
        print("MCP allowed:", sorted(list(mcp_tool_names)))
        # print("MCP tools text:\n", tools_text)

    # --- LLM: ВАЖНО — без bind_tools() (это B-режим) ---
    llm = ChatOpenAI(
        model=s.model,
        base_url=s.base_url,
        api_key=s.api_key,
        temperature=s.temperature,
    )

    planner = create_planner_node(llm, tools_text, debug_dir=debug_dir)
    assistant = create_assistant_node(llm, s, mcp_tools, debug_dir=debug_dir)
    run_tool = create_tool_runner_node(s, mcp_tool_names)
    route_after_assistant = create_route_after_assistant_node()

    builder = StateGraph(AgentState)
    builder.add_node("planner", planner)
    builder.add_node("assistant", assistant)
    builder.add_node("run_tool", run_tool)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "assistant")
    builder.add_conditional_edges("assistant",
                                  route_after_assistant,
                                  {"run_tool": "run_tool", END: END})
    builder.add_edge("run_tool", "assistant")

    return builder.compile(checkpointer=checkpointer)
