import os
import asyncio
from datetime import datetime

import requests
from aiohttp import web
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, Application
)

BOT_TOKEN = os.getenv("8158547630:AAHXDP-vH6Y2T6IU3Du__n3MjA55ETZ30Kg")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://{os.getenv('https://telegram-site-checker1.onrender.com')}{WEBHOOK_PATH}"

active_users = set()


class SiteChecker:
    def __init__(self):
        self.sites = self.load_sites()

    def load_sites(self):
        try:
            with open('sites_list.txt', 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            return []

    def check_site(self, url):
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False

    async def auto_check(self, context: ContextTypes.DEFAULT_TYPE):
        down_sites = [site for site in self.sites if not self.check_site(site)]
        if down_sites:
            text = f"❌ Недоступные сайты ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):\n" + "\n".join(down_sites)
            for user_id in active_users:
                try:
                    await context.bot.send_message(chat_id=user_id, text=text)
                except Exception as e:
                    print(f"Ошибка отправки {user_id}: {e}")

    async def manual_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        report = [f"🔍 Проверка сайтов ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):"]
        all_up = True
        for site in self.sites:
            is_up = self.check_site(site)
            if not is_up:
                all_up = False
            report.append(f"{site}: {'✅' if is_up else '❌'}")

        if all_up:
            report.append("\n🎉 Все сайты работают!")

        await context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(report))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_chat.id
        active_users.add(user_id)
        await context.bot.send_message(chat_id=user_id, text="✅ Вы подписались на авто-проверку. /stop — отписаться.")

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_chat.id
        if user_id in active_users:
            active_users.remove(user_id)
            await context.bot.send_message(chat_id=user_id, text="🛑 Вы отписались от авто-проверки.")
        else:
            await context.bot.send_message(chat_id=user_id, text="ℹ️ Вы не были подписаны.")


async def main():
    checker = SiteChecker()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", checker.start_command))
    app.add_handler(CommandHandler("check", checker.manual_check))
    app.add_handler(CommandHandler("stop", checker.stop_command))

    app.job_queue.run_repeating(checker.auto_check, interval=3600, first=10)

    async def handle(request):
        data = await request.json()
        await app.update_queue.put(Update.de_json(data, app.bot))
        return web.Response()

    aio_app = web.Application()
    aio_app.add_routes([web.post(WEBHOOK_PATH, handle)])

    await app.bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")

    runner = web.AppRunner(aio_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
