import requests
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, Application
)
import nest_asyncio

nest_asyncio.apply()

BOT_TOKEN = "8158547630:AAHXDP-vH6Y2T6IU3Du__n3MjA55ETZ30Kg"  # ← ЗАМЕНИ на свой токен от BotFather

active_users = set()

class SiteChecker:
    def __init__(self):
        self.sites = self.load_sites()

    def load_sites(self):
        try:
            with open('sites_list.txt', 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print("⚠️ Файл sites_list.txt не найден.")
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

        if not down_sites:
            return

        text = f"❌ Обнаружены недоступные сайты ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):\n"
        text += "\n".join(down_sites)

        for user_id in active_users:
            try:
                await context.bot.send_message(chat_id=user_id, text=text)
            except Exception as e:
                print(f"Ошибка отправки пользователю {user_id}: {e}")

    async def manual_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        report = [f"🔍 Ручная проверка сайтов ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}):"]
        for site in self.sites:
            status = "✅ Доступен" if self.check_site(site) else "❌ Не доступен"
            report.append(f"{site}: {status}")

        await context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(report))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_chat.id
        active_users.add(user_id)
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Вы подписались на автоматическую проверку. Чтобы остановить — команда /stop"
        )

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_chat.id
        if user_id in active_users:
            active_users.remove(user_id)
            await context.bot.send_message(chat_id=user_id, text="🛑 Вы отписались от уведомлений.")
        else:
            await context.bot.send_message(chat_id=user_id, text="ℹ️ Вы не были подписаны.")

async def main():
    app: Application = ApplicationBuilder().token(BOT_TOKEN).build()
    checker = SiteChecker()

    # Команды
    app.add_handler(CommandHandler("start", checker.start_command))
    app.add_handler(CommandHandler("check", checker.manual_check))
    app.add_handler(CommandHandler("stop", checker.stop_command))

    # Автопроверка раз в час
    app.job_queue.run_repeating(checker.auto_check, interval=3600, first=10)

    print("✅ Бот запущен.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
