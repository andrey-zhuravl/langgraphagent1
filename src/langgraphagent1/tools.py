from __future__ import annotations

from datetime import datetime, timezone
from langchain_core.tools import tool


@tool
def get_utc_time() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


@tool
def echo(text: str) -> str:
    """Echo input text back."""
    return text
