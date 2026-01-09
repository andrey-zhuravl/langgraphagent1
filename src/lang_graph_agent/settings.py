from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()
redis_url: str = os.environ.get("REDIS_URL")
DIR_DEBUG: str = 'debug'


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.2
    max_steps: int = 6
    debug: bool = False
    # Показать модели ТОЛЬКО эти MCP tools (иначе она “плавает” в огромном списке)
    mcp_allowed_tools_csv: str = "get_utc_time,echo"


def load_settings() -> Settings:
    return Settings(
        base_url=os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1"),
        api_key=os.environ.get("OPENAI_API_KEY", "local-key"),
        model=os.environ.get("OPENAI_MODEL", "local-model"),
        max_steps=int(os.environ.get("AGENT_MAX_STEPS", "6")),
        debug=os.environ.get("DEBUG_AGENT", "0") == "1",
        mcp_allowed_tools_csv=os.environ.get("MCP_ALLOWED_TOOLS", "get_utc_time,echo"),
    )

def _parse_allowed(csv: str) -> set[str]:
    """Парсит CSV в set инструментов."""
    items = [x.strip() for x in (csv or "").split(",")]
    return {x for x in items if x}
