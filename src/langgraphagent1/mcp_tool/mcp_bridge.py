import os
from typing import Any
from mcp.types import Tool as McpTool
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential
from src.langgraphagent1.mcp_tool.mcp_client import McpStreamClient


class McpToolAdapter(BaseModel):
    name: str
    description: str | None = None
    input_schema: dict
    output_schema: dict | None = None

    def __init__(self, mcp_tool: McpTool):
        super().__init__(
            name=mcp_tool.name,
            description=mcp_tool.description,
            input_schema=mcp_tool.inputSchema,
            output_schema=mcp_tool.outputSchema
        )

    def _run(self, tool_args: dict) -> Any:
        # Вызов MCP инструмента через асинхронный метод
        return call_tool_sync(self.name, tool_args)  # или async-версия для асинхронных инструментов

    def to_openai_tool(self) -> dict:
        """Преобразуем инструмент в формат OpenAI (JSON schema)"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.input_schema.get("properties", {}),
                "required": self.input_schema.get("required", []),
            },
        }


def _mcp_url() -> str:
    return os.environ.get("MCP_URL", "http://127.0.0.1:8000/mcp")


async def _list_tools_async() -> list[Any]:
    async with McpStreamClient(_mcp_url()) as c:
        return await c.list_tools()


async def _call_tool_async(name: str, args: dict[str, Any]) -> Any:
    async with McpStreamClient(_mcp_url()) as c:
        return await c.call_tool(name, args)


# --- MCP tools: берём список, фильтруем, показываем модели ---
@retry(
    reraise=True,
    stop=stop_after_attempt(6),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
)
async def safe_list_tools():
    return await list_tools_sync()


async def list_tools_sync() -> list[Any]:
    return await _list_tools_async()


async def call_tool_sync(name: str, args: dict[str, Any]) -> Any:
    return await _call_tool_async(name, args)


def render_tools_for_prompt(tools: list[Any]) -> str:
    lines: list[str] = []
    for t in tools:
        props = (t.inputSchema or {}).get("properties", {}) or {}
        params = ", ".join(props.keys())
        desc = (t.description or "").strip()
        if desc:
            lines.append(f"- {t.name}({params}): {desc}")
        else:
            lines.append(f"- {t.name}({params})")
    return "\n".join(lines)


def render_tools_name_for_prompt(tools: list[Any]) -> str:
    lines: list[str] = []
    for t in tools:
        lines.append(f"- {t.name}")
    return "\n".join(lines)
