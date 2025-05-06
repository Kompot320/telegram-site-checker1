import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests

DEFAULT_CONFIG = {
    'BOT_TOKEN': '8158547630:AAHXI6vOyekQ__paWkxPMMIzs-ho7A71LUs'
}

class SiteChecker:
    def __init__(self, config):
        self.config = config
        self.sites = self.load_sites()
        
    def load_sites(self):
        try:
            with open('sites_list.txt', 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print("⚠️ Файл sites_list.txt не найден! Создайте его с списком сайтов.")
            return []

    def check_site(self, url):
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False

    async def send_report(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        if not self.sites:
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Список сайтов пуст! Добавьте сайты в sites_list.txt"
            )
            return

        report = [f"🔍 Проверка сайтов {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:"]
        for site in self.sites:
            status = "✅ Доступен" if self.check_site(site) else "❌ Не доступен"
            report.append(f"{site}: {status}")

        await context.bot.send_message(
            chat_id=chat_id,
            text="\n".join(report)
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id  # 👈 получаем ID пользователя
        await context.bot.send_message(
            chat_id=chat_id,
            text="🟢 Запускаю проверку сайтов..."
        )
        await self.send_report(context, chat_id)

async def main():
    checker = SiteChecker(DEFAULT_CONFIG)
    
    app = Application.builder().token(DEFAULT_CONFIG['BOT_TOKEN']).build()
    app.add_handler(CommandHandler("start", checker.start))
    
    print("🤖 Бот запущен. Отправьте /start в Telegram для проверки сайтов")
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
