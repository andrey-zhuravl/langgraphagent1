import os
import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters
)

from src.langgraphagent1.agent import run_once
from src.langgraphagent1.metrics.service import MetricsService

#загружаем конфиг
load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("tg-gateway")

BOT_TOKEN = os.environ.get("TG_BOT_TOKEN").strip()

# Жёсткая защита: разрешённые user_id (оставь пустым set(), если не нужно)
ALLOWED_USER_IDS = set()  # например: {123456789}

# Чтобы в одном чате не запускалось 2 параллельных прогона агента
_chat_locks: Dict[int, asyncio.Lock] = {}

metrics = MetricsService()

def chat_lock(chat_id: int) -> asyncio.Lock:
    lock = _chat_locks.get(chat_id)
    if lock is None:
        lock = asyncio.Lock()
        _chat_locks[chat_id] = lock
    return lock


@dataclass
class AgentResponse:
    text: str

step = 1
async def call_agent(text: str, thread_id: str, meta: dict) -> AgentResponse:
    global step
    time = datetime.now(timezone.utc).isoformat()
    task_id = uuid.uuid4()
    await metrics.create_task(task_id=task_id, name=text, content=text, thread_id=thread_id)
    result = await run_once(text,
                            debug_dir=f"task_{time[:19].replace(':','-')}_{step}",
                            thread_id=thread_id,
                            task_id=task_id)
    planned = result.get("tools", []) or []  # planner возвращает tools:contentReference[oaicite:6]{index=6}
    used = result.get("tools_used", []) or []
    events = result.get("llm_usage_events", []) or []

    await metrics.finalize_task_and_save_usage(
        task_id=task_id,
        planned_tools=planned,
        used_tools=used,
        usage_events=events,
        success=True,
        error=None,
    )

    answer = result["messages"][-1]
    answer_text = (getattr(answer, "content", "") or "").strip()
    if answer_text.startswith("FINAL:"):
        answer_text = answer_text[len("FINAL:"):]
    print(f"call_agent = {text}")
    step=step+1
    return AgentResponse(text=f"{answer_text}")

async def send_large_message(chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE):
    # Разбиваем текст на части по 4096 символов

    print("Разбиваем текст на части по 4096 символов")
    max_message_length = 4096
    for i in range(0, len(text), max_message_length):
        part = text[i:i + max_message_length]
        await context.bot.send_message(chat_id=chat_id, text=part)

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return

    msg = update.message
    if msg is None or msg.text is None:
        return

    chat_id = update.effective_chat.id
    thread_id = f"tg:{chat_id}"
    text = msg.text.strip()

    meta = {
        "user_id": update.effective_user.id if update.effective_user else None,
        "username": update.effective_user.username if update.effective_user else None,
        "chat_id": chat_id,
        "message_id": msg.message_id,
        "chat_type": update.effective_chat.type,
    }

    lock = chat_lock(chat_id)
    async with lock:
        # Показываем "typing..."
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        print("Показываем on_text")

        try:
            resp = await call_agent(text=text, thread_id=thread_id, meta=meta)
            await send_large_message(chat_id, resp.text, context)  # Отправка больших сообщений
        except Exception as e:
            log.exception("Agent call failed")
            await msg.reply_text(f"Ошибка при вызове агента: {e}")

def is_allowed(update: Update) -> bool:
    if not ALLOWED_USER_IDS:
        return True
    uid = update.effective_user.id if update.effective_user else None
    return uid in ALLOWED_USER_IDS


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    await update.message.reply_text(
        "Я шлюз к твоему агенту.\n"
        "Пиши сообщение — я передам агенту.\n\n"
        "Команды:\n"
        "/help\n"
        "/reset (если ты реализуешь сброс в агенте)\n"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    await update.message.reply_text(
        "Отправь текст — получишь ответ агента.\n"
        "Можно делать команды вида:\n"
        "  /cmd <что-то>\n\n"
        "MVP команды:\n"
        "/reset — сбросить контекст (нужно подключить в агенте)\n"
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return

    chat_id = update.effective_chat.id
    thread_id = f"tg:{chat_id}"

    # Тут ты должен сбросить память/чекпоинт для thread_id.
    # Как именно — зависит от твоего checkpointer/storage.
    # Например: await asyncio.to_thread(memory.clear, thread_id)
    await update.message.reply_text(f"Сброс для {thread_id}: сделай реализацию в своём агенте.")


async def on_text1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return

    msg = update.message
    if msg is None or msg.text is None:
        return

    chat_id = update.effective_chat.id
    thread_id = f"tg:{chat_id}"
    text = msg.text.strip()

    meta = {
        "user_id": update.effective_user.id if update.effective_user else None,
        "username": update.effective_user.username if update.effective_user else None,
        "chat_id": chat_id,
        "message_id": msg.message_id,
        "chat_type": update.effective_chat.type,
    }

    lock = chat_lock(chat_id)
    async with lock:
        # Показываем "typing..."
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        try:
            resp = await call_agent(text=text, thread_id=thread_id, meta=meta)
            await msg.reply_text(resp.text)
        except Exception as e:
            log.exception("Agent call failed")
            await msg.reply_text(f"Ошибка при вызове агента: {e}")


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Set TG_BOT_TOKEN env var")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("Telegram gateway started (long polling)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
