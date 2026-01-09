from telegram import Update
from telegram.ext import ContextTypes

# Жёсткая защита: разрешённые user_id (оставь пустым set(), если не нужно)
# например: {123456789}
ALLOWED_USER_IDS = set()


def is_allowed(update: Update) -> bool:
    if not ALLOWED_USER_IDS:
        return True
    uid = update.effective_user.id if update.effective_user else None
    return uid in ALLOWED_USER_IDS


async def send_large_message(chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE):
    # Разбиваем текст на части по 4096 символов

    print("Разбиваем текст на части по 4096 символов")
    max_message_length = 4096
    for i in range(0, len(text), max_message_length):
        part = text[i:i + max_message_length]
        await context.bot.send_message(chat_id=chat_id, text=part)
