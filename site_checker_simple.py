import os
import asyncio
from datetime import datetime
import requests

from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, Application
)

BOT_TOKEN = "8158547630:AAHXDP-vH6Y2T6IU3Du__n3MjA55ETZ30Kg"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://telegram-site-checker1.onrender.com{WEBHOOK_PATH}"

active_users = set()


class SiteChecker:
    def __init__(self):
        self.sites = self.load_sites()
        self.site_status = {site: None for site in self.sites}  # None = unknown, True = up, False = down

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

    def log_status_change(self, site, status):
        with open("down_log.txt", "a") as f:
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if status:
                f.write(f"{time_str} — ✅ Восстановлен: {site}\n")
            else:
                f.write(f"{time_str} — ❌ Упал: {site}\n")

    async def auto_check(self, context: ContextTypes.DEFAULT_TYPE):
        for site in self.sites:
            is_up = self.check_site(site)
            prev_status = self.site_status.get(site)

            # Только если статус изменился
            if prev_status is not None and prev_status != is_up:
                self.site_status[site] = is_up
                self.log_status_change(site, is_up)

                status_text = (
                    f"✅ Сайт снова работает: {site}" if is_up
                    else f"❌ Сайт упал: {site}"
                )

                for user_id in active_users:
                    try:
                        await context.bot.send_message(chat_id=user_id, text=status_text)
                    except Exception as e:
                        print(f"Ошибка при отправке пользователю {user_id}: {e}")

            else:
                self.site_status[site] = is_up  # обновляем статус

    async def manual_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        report = [f"🔍 Ручная проверка сайтов ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):"]
        all_up = True

        for site in self.sites:
            is_up = self.check_site(site)
            self.site_status[site] = is_up
            if not is_up:
                all_up = False
            report.append(f"{site}: {'✅' if is_up else '❌'}")

        if all_up:
            report.append("\n🎉 Все сайты работают!")

        await update.message.reply_text("\n".join(report), reply_markup=self.get_keyboard())

    async def show_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        report = [f"📊 Статус сайтов:"]
        for site in self.sites:
            status = self.site_status.get(site)
            report.append(f"{site}: {'✅' if status else '❌' if status is False else '❓ неизвестно'}")

        await update.message.reply_text("\n".join(report), reply_markup=self.get_keyboard())

    def get_keyboard(self):
        keyboard = [
            [
                InlineKeyboardButton("🔄 Проверить сейчас", callback_data="check_now"),
                InlineKeyboardButton("📊 Статус сайтов", callback_data="status"),
                InlineKeyboardButton("⛔ Остановить", callback_data="stop")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def handle_buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == "check_now":
            await self.manual_check(update, context)
        elif query.data == "status":
            await self.show_status(update, context)
        elif query.data == "stop":
            user_id = query.from_user.id
            active_users.discard(user_id)
            await query.edit_message_text("🛑 Вы отписались от авто-проверки.")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_chat.id
        active_users.add(user_id)
        await update.message.reply_text(
            "✅ Вы подписались на авто-проверку.",
            reply_markup=self.get_keyboard()
        )

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_chat.id
        active_users.discard(user_id)
        await context.bot.send_message(chat_id=user_id, text="🛑 Вы отписались от авто-проверки.")


async def main():
    checker = SiteChecker()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", checker.start_command))
    app.add_handler(CommandHandler("check", checker.manual_check))
    app.add_handler(CommandHandler("stop", checker.stop_command))
    app.add_handler(CommandHandler("status", checker.show_status))
    app.add_handler(CallbackQueryHandler(checker.handle_buttons))

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
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
