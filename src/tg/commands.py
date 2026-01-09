from telegram import Update
from telegram.ext import ContextTypes

from src.tg.tg_utils import is_allowed


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
