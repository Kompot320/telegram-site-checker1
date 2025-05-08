import aiohttp
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime

# ==== НАСТРОЙКИ ====
TOKEN = '6611255147:AAEqcMrYpbyGB0vWaSPvDKloNcs2VpUp5DI'
WEBHOOK_URL = 'https://arbin.online/api/bot'
CHECK_INTERVAL = 60  # Интервал в секундах между проверками сайтов

# ==== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====
user_sites = {}  # {user_id: [url1, url2]}
log_file = "down_log.txt"

# ==== ФУНКЦИИ ====

async def check_sites(context: ContextTypes.DEFAULT_TYPE):
    for user_id, sites in user_sites.items():
        for site in sites:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(site, timeout=10) as response:
                        if response.status != 200:
                            await notify_down(user_id, site, response.status)
            except Exception as e:
                await notify_down(user_id, site, str(e))

async def notify_down(user_id: int, site: str, error):
    message = f"❌ Сайт недоступен: {site} (ошибка: {error})"
    await application.bot.send_message(chat_id=user_id, text=message)
    with open(log_file, "a") as f:
        f.write(f"[{datetime.now()}] {message}\n")

# ==== КОМАНДЫ ====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь /add <url>, чтобы добавить сайт для мониторинга.")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) != 1:
        return await update.message.reply_text("Формат: /add https://example.com")
    
    url = context.args[0]
    if user_id not in user_sites:
        user_sites[user_id] = []
    if url not in user_sites[user_id]:
        user_sites[user_id].append(url)
        await update.message.reply_text(f"✅ Сайт добавлен: {url}")
    else:
        await update.message.reply_text("Сайт уже добавлен.")

async def list_sites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sites = user_sites.get(user_id, [])
    if not sites:
        await update.message.reply_text("У вас нет сайтов в списке.")
    else:
        await update.message.reply_text("📋 Ваши сайты:\n" + "\n".join(sites))

# ==== ГЛАВНАЯ ====

application = ApplicationBuilder().token(TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("add", add))
application.add_handler(CommandHandler("list", list_sites))

async def main():
    # Устанавливаем Webhook
    await application.bot.set_webhook(url=WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")

    # Запускаем задачу мониторинга
    job_queue = application.job_queue
    job_queue.run_repeating(check_sites, interval=CHECK_INTERVAL, first=10)

    await application.initialize()
    await application.start()
    await application.updater.start_polling()  # на случай, если webhook не сработает
    await application.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())
