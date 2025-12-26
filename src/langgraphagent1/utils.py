from __future__ import annotations

import base64
import hashlib
import os

from dotenv import load_dotenv

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import APIConnectionError

from src.langgraphagent1.mcp_tool.mcp_bridge import (
    call_tool_sync,
)

load_dotenv()
redis_url: str = os.environ.get("REDIS_URL")
DIR_DEBUG: str = 'debug'


@retry(
    reraise=True,
    stop=stop_after_attempt(6),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
    retry=retry_if_exception_type(APIConnectionError),
)
def safe_invoke(llm: ChatOpenAI, messages: list[BaseMessage]):
    return llm.invoke(messages)

@retry(
    reraise=True,
    stop=stop_after_attempt(6),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
)
async def safe_call_tool(name: str, args: dict):
    return await call_tool_sync(name, args)

def _adapt_write_file_args(args: dict) -> dict:
    """
    Делает write_file железобетонным:
    - принимает как старый формат: {"file_path":..., "content": "..."}
    - преобразует в новый: content=base64, content_encoding="base64", sha256=...
    - если LLM прислала \\n вместо переносов — аккуратно чинит (эвристика).
    """
    a = dict(args or {})

    # поддержим возможные имена полей
    file_path = a.get("file_path") or a.get("path")
    content = a.get("content")

    if not isinstance(content, str):
        return a

    # если уже base64 — не трогаем
    if a.get("content_encoding") == "base64":
        return a

    # 1) аварийная починка двойного экранирования от LLM
    #    (делаем только если реальных переносов нет, но есть "\\n")
    if "\n" not in content and "\\n" in content:
        content = (
            content
            .replace("\\r\\n", "\n")
            .replace("\\n", "\n")
            .replace("\\t", "\t")
        )

    # 2) переводим в bytes -> base64 + sha256
    data = content.encode("utf-8")
    a["content"] = base64.b64encode(data).decode("ascii")
    a["content_encoding"] = "base64"
    a["sha256"] = hashlib.sha256(data).hexdigest()

    # newline-policy при base64 не нужен (байты уже готовы)
    a.pop("newline", None)

    # если у тебя MCP требует строго file_path — убедимся, что он есть
    if file_path is not None:
        a["file_path"] = file_path

    return a