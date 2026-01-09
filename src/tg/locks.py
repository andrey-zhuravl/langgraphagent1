import asyncio
from typing import Dict

# Чтобы в одном чате не запускалось 2 параллельных прогона агента
_chat_locks: Dict[int, asyncio.Lock] = {}

def chat_lock(chat_id: int) -> asyncio.Lock:
    lock = _chat_locks.get(chat_id)
    if lock is None:
        lock = asyncio.Lock()
        _chat_locks[chat_id] = lock
    return lock
