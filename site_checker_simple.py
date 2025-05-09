import logging
import aiohttp
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from datetime import datetime

API_TOKEN = '8158547630:AAHXDP-vH6Y2T6IU3Du__n3MjA55ETZ30Kg'  # ← Вставьте сюда токен вашего бота

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Храним сайты и статусы по пользователям
user_sites = {}
user_status = {}
user_tasks = {}

# Логгер
logging.basicConfig(level=logging.INFO)

# Кнопки управления
def get_main_keyboard():
    buttons = [
        InlineKeyboardButton("🔄 Проверить сейчас", callback_data="check_now"),
        InlineKeyboardButton("📊 Статус сайтов", callback_data="status"),
        InlineKeyboardButton("⛔ Остановить авто-проверку", callback_data="stop")
    ]
    return InlineKeyboardMarkup(row_width=1).add(*buttons)

# Проверка сайта
async def check_site(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                return response.status == 200
    except Exception:
        return False

# Отправка уведомления при изменении статуса
async def notify_changes(user_id):
    for url in user_sites[user_id]:
        is_up = await check_site(url)
        if user_status[user_id].get(url) != is_up:
            status = "🟢 Доступен" if is_up else "🔴 Недоступен"
            await bot.send_message(user_id, f"⚠️ Изменение статуса: {url}\nНовый статус: {status}")
            user_status[user_id][url] = is_up
            if not is_up:
                with open("down_log.txt", "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now()} — {url} стал недоступен\n")

# Фоновая задача для авто-проверки
async def monitoring_task(user_id):
    while True:
        await notify_changes(user_id)
        await asyncio.sleep(60)

# /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    await message.answer("Привет! Отправь список сайтов через пробел или запятую, которые хочешь мониторить.")
    if user_id in user_tasks and not user_tasks[user_id].done():
        user_tasks[user_id].cancel()
    user_sites[user_id] = []
    user_status[user_id] = {}

# Принимаем список сайтов
@dp.message_handler(lambda message: message.from_user.id in user_sites and not user_sites[message.from_user.id])
async def receive_sites(message: types.Message):
    user_id = message.from_user.id
    text = message.text.replace(',', ' ').split()
    user_sites[user_id] = text
    user_status[user_id] = {}
    await message.answer("✅ Мониторинг запущен!", reply_markup=get_main_keyboard())
    # Инициализируем статус
    for url in text:
        is_up = await check_site(url)
        user_status[user_id][url] = is_up
    # Запуск фоновой задачи
    task = asyncio.create_task(monitoring_task(user_id))
    user_tasks[user_id] = task

# Inline-кнопки
@dp.callback_query_handler(lambda c: c.data in ["check_now", "status", "stop"])
async def callback_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if data == "check_now":
        await notify_changes(user_id)
        await bot.answer_callback_query(callback_query.id, text="Проверка завершена.")

    elif data == "status":
        text = ""
        for url in user_sites.get(user_id, []):
            status = user_status[user_id].get(url, False)
            emoji = "🟢" if status else "🔴"
            text += f"{emoji} {url}\n"
        await bot.send_message(user_id, f"📊 Текущий статус сайтов:\n{text}")

    elif data == "stop":
        if user_id in user_tasks:
            user_tasks[user_id].cancel()
            await bot.send_message(user_id, "⛔ Авто-проверка остановлена.")
        else:
            await bot.send_message(user_id, "⚠️ Авто-проверка не была запущена.")

    await bot.answer_callback_query(callback_query.id)

# Запуск
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
