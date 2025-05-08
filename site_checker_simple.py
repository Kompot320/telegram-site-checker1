import asyncio
import datetime
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from aiohttp import web
import os

API_TOKEN = '8158547630:AAHXDP-vH6Y2T6IU3Du__n3MjA55ETZ30Kg'  # Вставлен твой токен

# Хранилища
user_sites = {}       # {user_id: [url1, url2, ...]}
user_statuses = {}    # {user_id: {url: bool}}

CHECK_INTERVAL = 3600  # Интервал для проверки доступности (60 минут)


# Логирование изменения статуса сайта
def log_status_change(user_id, url, is_up):
    status = "UP" if is_up else "DOWN"
    time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("down_log.txt", "a") as log_file:
        log_file.write(f"{time_str} | User {user_id} | {url} is {status}\n")


# Проверка доступности сайта
async def check_site(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                return resp.status < 400
    except:
        return False


# Отправка сообщения о статусе сайта пользователю
async def send_site_status(user_id, bot, url, is_up):
    msg = f"✅ Сайт снова доступен: {url}" if is_up else f"⛔ Сайт недоступен: {url}"
    await bot.send_message(chat_id=user_id, text=msg)


# Основная функция для проверки всех сайтов
async def check_all_users(bot):
    while True:
        for user_id, urls in user_sites.items():
            for url in urls:
                is_up = await check_site(url)
                last_status = user_statuses[user_id].get(url)

                if last_status is None:
                    user_statuses[user_id][url] = is_up
                elif last_status != is_up:
                    user_statuses[user_id][url] = is_up
                    log_status_change(user_id, url, is_up)
                    await send_site_status(user_id, bot, url, is_up)

        await asyncio.sleep(CHECK_INTERVAL)


# Стартовая команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sites:
        user_sites[user_id] = ['https://example.com']
        user_statuses[user_id] = {}

    buttons = [
        [InlineKeyboardButton("🔄 Проверить сейчас", callback_data='check_now')],
        [InlineKeyboardButton("📊 Статус сайтов", callback_data='status')],
        [InlineKeyboardButton("⛔ Остановить авто-проверку", callback_data='stop')]
    ]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🚀 Мониторинг запущен!", reply_markup=markup)


# Обработчик кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_sites:
        await query.edit_message_text("Сначала запустите /start")
        return

    if query.data == 'check_now':
        messages = []
        for url in user_sites[user_id]:
            is_up = await check_site(url)
            user_statuses[user_id][url] = is_up
            messages.append(f"{url} — {'✅ Доступен' if is_up else '⛔ Недоступен'}")
        await query.edit_message_text("Результат:\n" + '\n'.join(messages))

    elif query.data == 'status':
        messages = []
        for url in user_sites[user_id]:
            status = user_statuses[user_id].get(url)
            status_str = "❓ Неизвестно" if status is None else ("✅ Доступен" if status else "⛔ Недоступен")
            messages.append(f"{url} — {status_str}")
        await query.edit_message_text("Статус сайтов:\n" + '\n'.join(messages))

    elif query.data == 'stop':
        user_sites[user_id] = []
        await query.edit_message_text("⛔ Мониторинг остановлен. Введите /start для запуска.")


# Настроим Webhook и aiohttp сервер
async def run_webhook(application):
    webhook_url = "https://telegram-site-checker1.onrender.com/webhook"  # Вставлен твой URL
    await application.bot.set_webhook(webhook_url)

    async def handler(request):
        request_body = await request.text()
        await application.update_queue.put(request_body)
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_post('/webhook', handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080)))
    await site.start()


# Главная функция для запуска бота и проверки сайтов
async def main():
    app = Application.builder().token(API_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Запускаем фоновые задачи
    asyncio.create_task(check_all_users(app.bot))
    print("Бот запущен.")
    
    # Запускаем Webhook
    await run_webhook(app)

    # Запускаем бота в фоновом режиме
    await app.run_polling()


if __name__ == '__main__':
    asyncio.run(main())
