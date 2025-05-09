import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiohttp import web
import aiohttp
import asyncio
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)

subscribed_users = set()
site_status = {}
site_list_file = "sites_list.txt"
check_interval = 60

logging.basicConfig(level=logging.INFO)

def get_main_keyboard():
    buttons = [
        [KeyboardButton("🔄 Проверить сейчас")],
        [KeyboardButton("📊 Статус сайтов")],
        [KeyboardButton("⛔ Остановить авто-проверку")],
        [KeyboardButton("❌ Скрыть меню")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def load_sites():
    if not os.path.exists(site_list_file):
        return []
    with open(site_list_file, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

async def check_site(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                return response.status == 200
    except Exception:
        return False

async def notify_all_users(message):
    for user_id in subscribed_users:
        try:
            await bot.send_message(user_id, message)
        except Exception:
            pass

async def monitor_sites():
    while True:
        sites = load_sites()
        for site in sites:
            is_up = await check_site(site)
            if site not in site_status:
                site_status[site] = is_up
            elif site_status[site] != is_up:
                status = "🟢 снова доступен" if is_up else "🔴 стал недоступен"
                msg = f"⚠️ {site} {status}"
                await notify_all_users(msg)
                site_status[site] = is_up
                if not is_up:
                    with open("down_log.txt", "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now()} — {site} стал недоступен\n")
        await asyncio.sleep(check_interval)

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    subscribed_users.add(user_id)
    await message.answer("✅ Вы подключены к мониторингу сайтов.", reply_markup=get_main_keyboard())

@dp.message_handler(lambda message: message.text in [
    "🔄 Проверить сейчас", "📊 Статус сайтов", "⛔ Остановить авто-проверку", "❌ Скрыть меню"])
async def handle_main_menu(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    sites = load_sites()

    if text == "🔄 Проверить сейчас":
        result = ""
        for site in sites:
            is_up = await check_site(site)
            emoji = "🟢" if is_up else "🔴"
            result += f"{emoji} {site}\n"
        await message.answer(f"📥 Результат проверки:\n{result}")

    elif text == "📊 Статус сайтов":
        result = ""
        for site in sites:
            is_up = site_status.get(site, False)
            emoji = "🟢" if is_up else "🔴"
            result += f"{emoji} {site}\n"
        await message.answer(f"📊 Текущий статус:\n{result}")

    elif text == "⛔ Остановить авто-проверку":
        subscribed_users.discard(user_id)
        await message.answer("⛔ Вы отписались от уведомлений.")

    elif text == "❌ Скрыть меню":
        await message.answer("Клавиатура скрыта.", reply_markup=ReplyKeyboardRemove())

# =======================
# Webhook routes
# =======================

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(monitor_sites())

async def on_shutdown(app):
    await bot.delete_webhook()

async def handle_webhook(request):
    data = await request.json()
    update = types.Update.to_object(data)
    await dp.process_update(update)
    return web.Response()

app = web.Application()
app.router.add_post('/webhook', handle_webhook)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == '__main__':
    web.run_app(app, port=int(os.environ.get("PORT", 10000)))


