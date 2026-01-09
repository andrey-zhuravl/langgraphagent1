import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)

from src.tg.agent import call_agent
from src.tg.commands import cmd_start, cmd_help, cmd_reset
from src.tg.locks import chat_lock
from src.tg.tg_utils import is_allowed, send_large_message

#загружаем конфиг
load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("tg-gateway")

BOT_TOKEN = os.environ.get("TG_BOT_TOKEN").strip()

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
