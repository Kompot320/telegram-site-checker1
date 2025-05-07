import asyncio
from datetime import datetime
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes

# Конфигурация (должна быть выше)
DEFAULT_CONFIG = {
    'BOT_TOKEN': 'your_bot_token',  # Замените на ваш токен
    'CHAT_ID': 'your_chat_id'       # Замените на ваш chat_id
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
            print("⚠️ Файл sites_list.txt не найден!")
            return []

    def check_site(self, url):
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False

    async def send_report(self, context: ContextTypes.DEFAULT_TYPE):
        if not self.sites:
            await context.bot.send_message(
                chat_id=self.config['CHAT_ID'],
                text="⚠️ Список сайтов пуст!"
            )
            return

        report = [f"🔍 Проверка сайтов {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:"]
        for site in self.sites:
            status = "✅ Доступен" if self.check_site(site) else "❌ Не доступен"
            report.append(f"{site}: {status}")

        await context.bot.send_message(
            chat_id=self.config['CHAT_ID'],
            text="\n".join(report)
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🟢 Запускаю проверку сайтов..."
        )
        await self.send_report(context)

    async def manual_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.send_report(context)

    async def auto_check(self, context: ContextTypes.DEFAULT_TYPE):
        await self.send_report(context)

async def main():
    checker = SiteChecker(DEFAULT_CONFIG)

    app = Application.builder().token(DEFAULT_CONFIG['BOT_TOKEN']).build()

    # Устанавливаем команды в меню бота
    await app.bot.set_my_commands([
        BotCommand("start", "Запустить бота"),
        BotCommand("check", "Проверить сайты вручную"),
        BotCommand("stop", "Остановить авто-проверку")
    ])

    app.add_handler(CommandHandler("start", checker.start))
    app.add_handler(CommandHandler("check", checker.manual_check))  # ручная проверка
    app.add_handler(CommandHandler("stop", checker.auto_check))  # для остановки, если нужно, надо будет дописать логику

    # Запускаем авто-проверку
    app.job_queue.run_repeating(checker.auto_check, interval=3600, first=10)

    print("🤖 Бот запущен.")
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()

    asyncio.run(main())
