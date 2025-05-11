import logging
import aiohttp
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
from aiohttp import web

API_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(API_TOKEN)
dp = Dispatcher(bot)

subscribed_users = set()
site_status = {}
site_list_file = "sites_list.txt"
keywords_file = "site_keywords.txt"
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


def load_keywords():
    site_keywords = {}
    if not os.path.exists(keywords_file):
        return site_keywords
    with open(keywords_file, "r", encoding="utf-8") as f:
        for line in f:
            if '|' in line:
                url, keywords_str = line.split('|', 1)
                keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
                site_keywords[url.strip()] = keywords
    return site_keywords


async def check_site(url, keywords=[]):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    return False
                html = await response.text()
                for keyword in keywords:
                    if keyword not in html:
                        return False
                return True
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
        site_keywords = load_keywords()
        for site in sites:
            keywords = site_keywords.get(site, [])
            is_up = await check_site(site, keywords)
            if site not in site_status:
                site_status[site] = is_up
            elif site_status[site] != is_up:
                status = "🟢 снова доступен" if is_up else "🔴 стал недоступен или изменился"
                msg = f"⚠️ {site} {status}"
                await notify_all_users(msg)
                site_status[site] = is_up
                if not is_up:
                    with open("down_log.txt", "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now()} — {site} стал недоступен или изменился\n")
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
    site_keywords = load_keywords()

    if data == "check_now":
        result = ""
        for site in sites:
            keywords = site_keywords.get(site, [])
            is_up = await check_site(site, keywords)
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
        await bot.send_message(user_id, "⛔ Вы отписались от уведомлений.", reply_markup=get_main_keyboard())
        await bot.answer_callback_query(callback_query.id)


# HTTP-сервер для Render
async def render_healthcheck(request):
    return web.Response(text="Bot is running")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", render_healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000)))
    await site.start()
    print(f"🌐 Web-сервер запущен на порту {os.environ.get('PORT', 10000)}")


async def main():
    await start_web_server()
    asyncio.create_task(monitor_sites())
    await dp.start_polling()


if __name__ == '__main__':
    asyncio.run(main())
