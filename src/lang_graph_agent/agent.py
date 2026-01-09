from __future__ import annotations
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.redis import AsyncRedisSaver
from src.lang_graph_agent import filesystem_utils
from src.lang_graph_agent.graph_builder import build_graph
from src.lang_graph_agent.state import AgentState
from src.visual.to_png import save_langgraph_png2

load_dotenv()
redis_url: str = os.environ.get("REDIS_URL")

async def run_once(user_text: str,
                   *,
                   thread_id: str = "dev-thread",
                   debug_dir: str,
                   task_id: str) -> dict:
    filesystem_utils.create_directory(debug_dir)
    async with AsyncRedisSaver.from_conn_string(redis_url) as checkpointer:
        await checkpointer.adelete_thread(thread_id)
        graph = await build_graph(debug_dir, checkpointer)
        save_langgraph_png2(graph, "graph1.png")
        init_state: AgentState = {
            "task_id": task_id,
            "llm_usage_events": [],
            "tools_used": [],
            "general_task": user_text,
            "messages": [HumanMessage(content=user_text)],
            "llm_calls": 0,
            "plan": [],
            "steps": 0,
            "memory_summary": None,
        }
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 500,  # для 27 писем безопаснее 100–300
        }
        return await graph.ainvoke(init_state, config=config)
