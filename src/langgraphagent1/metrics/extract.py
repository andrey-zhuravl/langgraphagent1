from __future__ import annotations

from typing import Any, Optional, Tuple

from langchain_openai import ChatOpenAI


def extract_token_usage(ai_message: Any) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Возвращает (prompt_tokens, completion_tokens, total_tokens) из ответа LLM.
    НИЧЕГО не считаем руками.
    """
    usage_md = getattr(ai_message, "usage_metadata", None)
    if isinstance(usage_md, dict) and usage_md:
        # LangChain формат:
        # input_tokens/output_tokens/total_tokens
        return (
            usage_md.get("input_tokens"),
            usage_md.get("output_tokens"),
            usage_md.get("total_tokens"),
        )

    resp_md = getattr(ai_message, "response_metadata", None) or {}
    if isinstance(resp_md, dict):
        token_usage = resp_md.get("token_usage") or {}
        if isinstance(token_usage, dict) and token_usage:
            # OpenAI-совместимый формат:
            # prompt_tokens/completion_tokens/total_tokens
            return (
                token_usage.get("prompt_tokens"),
                token_usage.get("completion_tokens"),
                token_usage.get("total_tokens"),
            )

    return (None, None, None)

def extract_tokens(ai_message: Any, node: str, step: int, llm: ChatOpenAI,) -> dict:
    p,c,t = extract_token_usage(ai_message)
    event = {
        "node": node,
        "step": step,
        "model": getattr(llm, "model_name", None) or getattr(llm, "model", None),
        "prompt_tokens": p,
        "completion_tokens": c,
        "total_tokens": t,
    }
    return event