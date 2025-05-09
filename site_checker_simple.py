import asyncio
import logging
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
)
import nest_asyncio

# Применяем патч для работы в среде с уже активным event loop (как у Render)
nest_asyncio.apply()

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Твой токен Telegram-бота (НЕ ЗАБУДЬ заменить на свой)
TOKEN = '8158547630:AAHXDP-vH6Y2T6IU3Du__n3MjA55ETZ30Kg'

# Список сайтов для проверки
URLS = [
    'https://telegra.ph/Vash-Sayt-1',
    'https://telegra.ph/Vash-Sayt-2'
]


async def check_websites():
    """Проверка сайтов из списка URLS"""
    results = []
    for url in URLS:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                results.append(f"✅ {url} — Доступен")
            else:
                results.append(f"⚠️ {url} — Статус: {response.status_code}")
        except Exception as e:
            results.append(f"❌ {url} — Ошибка: {e}")
    return "\n".join(results)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я проверяю доступность сайтов. Используй /check чтобы начать.")


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = await check_websites()
    await update.message.reply_text(results)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if "проверить" in text:
        results = await check_websites()
        await update.message.reply_text(results)
    else:
        await update.message.reply_text("Я не понял. Напиши /check или 'проверить'.")


async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Бот запущен.")
    await app.run_polling()


# Запуск с учётом уже активного event loop (как на Render)
if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except RuntimeError:
        nest_asyncio.apply()
        asyncio.get_event_loop().run_until_complete(main())
