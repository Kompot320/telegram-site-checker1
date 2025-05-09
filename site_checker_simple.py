import logging
import aiohttp
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.dispatcher.webhook import get_new_configured_app
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.executor import start_webhook
from fastapi import FastAPI, Request
from aiogram.dispatcher.webhook import WebhookRequestHandler
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from datetime import datetime

API_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL")  # Render automatically sets this
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 10000))

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

subscribed_users = set()
site_status = {}
site_list_file = "sites_list.txt"
check_interval = 60  # секунд

logging.basicConfig(level=logging.INFO)

def get_main_keyboard():
    buttons = [
        InlineKeyboardButton("🔄 Проверить сейчас", callback_data="check_now"),
        InlineKeyboardButton("📊 Статус сайтов", callback_data="status"),
        InlineKeyboardButton("⛔ Остановить авто-проверку", callback_data="stop")
    ]
    return InlineKeyboardMarkup(row_width=1).add(*buttons)

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
            await bot.send_message(user_id, message, reply_markup=get_main_keyboard())
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

@dp.callback_query_handler(lambda c: c.data in ["check_now", "status", "stop"])
async def callback_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data
    sites = load_sites()

    if data == "check_now":
        result = ""
        for site in sites:
            is_up = await check_site(site)
            emoji = "🟢" if is_up else "🔴"
            result += f"{emoji} {site}\n"
        await bot.send_message(user_id, f"📥 Результат проверки:\n{result}", reply_markup=get_main_keyboard())
        await bot.answer_callback_query(callback_query.id)

    elif data == "status":
        result = ""
        for site in sites:
            is_up = site_status.get(site, False)
            emoji = "🟢" if is_up else "🔴"
            result += f"{emoji} {site}\n"
        await bot.send_message(user_id, f"📊 Текущий статус:\n{result}", reply_markup=get_main_keyboard())
        await bot.answer_callback_query(callback_query.id)

    elif data == "stop":
        subscribed_users.discard(user_id)
        await bot.send_message(user_id, "⛔ Вы отписались от уведомлений.")
        await bot.answer_callback_query(callback_query.id)

# FastAPI app
app = FastAPI()

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(monitor_sites())
    logging.info("Webhook set and monitoring started.")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    update = await request.json()
    telegram_update = types.Update.to_object(update)
    await dp.process_update(telegram_update)
    return {"ok": True}



