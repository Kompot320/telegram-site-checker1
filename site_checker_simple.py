import asyncio
import datetime
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
import os

API_TOKEN = '8158547630:AAHXDP-vH6Y2T6IU3Du__n3MjA55ETZ30Kg'

CHECK_INTERVAL = 3600  # интервал в секундах (60 минут)

user_statuses = {}  # {user_id: {url: bool}}

SITES_FILE = 'сайт/sites_list.txt'


def log_status_change(user_id, url, is_up):
    status = "UP" if is_up else "DOWN"
    time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("down_log.txt", "a") as log_file:
        log_file.write(f"{time_str} | User {user_id} | {url} is {status}\n")


def load_sites():
    if not os.path.exists(SITES_FILE):
        return []
    with open(SITES_FILE, 'r') as f:
        return [line.strip() for line in f if line.strip()]


async def check_site(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                return resp.status < 400
    except:
        return False


async def send_site_status(user_id, bot, url, is_up):
    msg = f"✅ Сайт снова доступен: {url}" if is_up else f"⛔ Сайт недоступен: {url}"
    await bot.send_message(chat_id=user_id, text=msg)


async def check_all_users(bot):
    while True:
        sites = load_sites()
        for user_id in user_statuses:
            for url in sites:
                is_up = await check_site(url)
                last_status = user_statuses[user_id].get(url)

                if last_status is None:
                    user_statuses[user_id][url] = is_up
                elif last_status != is_up:
                    user_statuses[user_id][url] = is_up
                    log_status_change(user_id, url, is_up)
                    await send_site_status(user_id, bot, url, is_up)
        await asyncio.sleep(CHECK_INTERVAL)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sites = load_sites()
    if not sites:
        await update.message.reply_text("⚠️ Не удалось загрузить сайты из файла.")
        return

    if user_id not in user_statuses:
        user_statuses[user_id] = {}

    buttons = [
        [InlineKeyboardButton("🔄 Проверить сейчас", callback_data='check_now')],
        [InlineKeyboardButton("📊 Статус сайтов", callback_data='status')],
        [InlineKeyboardButton("⛔ Остановить авто-проверку", callback_data='stop')]
    ]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🚀 Мониторинг запущен!", reply_markup=markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    sites = load_sites()
    if user_id not in user_statuses:
        await query.edit_message_text("Сначала запустите /start")
        return

    if query.data == 'check_now':
        messages = []
        for url in sites:
            is_up = await check_site(url)
            user_statuses[user_id][url] = is_up
            messages.append(f"{url} — {'✅ Доступен' if is_up else '⛔ Недоступен'}")
        await query.edit_message_text("Результат:\n" + '\n'.join(messages))

    elif query.data == 'status':
        messages = []
        for url in sites:
            status = user_statuses[user_id].get(url)
            status_str = "❓ Неизвестно" if status is None else ("✅ Доступен" if status else "⛔ Недоступен")
            messages.append(f"{url} — {status_str}")
        await query.edit_message_text("Статус сайтов:\n" + '\n'.join(messages))

    elif query.data == 'stop':
        user_statuses[user_id] = {}
        await query.edit_message_text("⛔ Мониторинг остановлен. Введите /start для запуска.")


async def main():
    app = Application.builder().token(API_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    asyncio.create_task(check_all_users(app.bot))
    print("Бот запущен.")
    await app.run_polling()


if __name__ == '__main__':
    asyncio.run(main())
