from typing import Any

from mcp import ClientSession, Tool
from mcp.client.streamable_http import streamablehttp_client

class McpStreamClient:
    def __init__(self, server_url: str):
        self.server_url = server_url
        self._inner_session: ClientSession | None = None
        self._transport = None
        self._read = None
        self._write = None

    async def __aenter__(self):
        self._transport = streamablehttp_client(self.server_url)
        self._read, self._write, _ = await self._transport.__aenter__()

        self._inner_session = ClientSession(self._read, self._write)
        await self._inner_session.__aenter__()
        await self._inner_session.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._inner_session:
            await self._inner_session.__aexit__(exc_type, exc_val, exc_tb)
        if self._transport:
            await self._transport.__aexit__(exc_type, exc_val, exc_tb)

    async def list_tools(self) -> list[Tool]:
        tools_result = await self._inner_session.list_tools()
        return tools_result.tools

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        try:
            result = await self._inner_session.call_tool(name, args)
        except Exception as e:
            print(e)

        if result.structuredContent is not None:
            return result.structuredContent

        if result.content:
            # превращаем TextContent[] в нормальную строку, чтобы LLM было видно
            texts = []
            for c in result.content:
                t = getattr(c, "text", None)
                if t is not None:
                    texts.append(t)
                else:
                    texts.append(str(c))
            return "\n".join(texts)

        return None
