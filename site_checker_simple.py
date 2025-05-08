import os
from aiohttp import web
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram.ext import ContextTypes
from telegram import Update

# Замените на ваш токен
BOT_TOKEN = "8158547630:AAHXDP-vH6Y2T6IU3Du__n3MjA55ETZ30Kg"
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://your-service-name.onrender.com{WEBHOOK_PATH}"

active_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    active_users.add(user_id)
    await update.message.reply_text("✅ Вы подписались на авто-проверку.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    active_users.discard(user_id)
    await update.message.reply_text("🛑 Вы отписались.")

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Проверка пока заглушка.")  # Замените на логику проверки

async def healthcheck(request):
    return web.Response(text="OK")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("check", check))

    await app.bot.set_webhook(url=WEBHOOK_URL)

    aio_app = web.Application()
    aio_app.router.add_post(WEBHOOK_PATH, app.webhook_handler())
    aio_app.router.add_get("/", healthcheck)  # простая проверка

    port = int(os.environ.get("PORT", 10000))  # Render передаёт PORT как переменную окружения
    print(f"✅ Запуск на порту {port}")
    web.run_app(aio_app, port=port)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
