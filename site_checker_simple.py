import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, JobQueue

# Получаем токен из переменной окружения
TOKEN = os.getenv('8191040502:AAHLup7zN6FoUfswuO43VT6wI3I1Yyy_wm0')  # Убедитесь, что переменная окружения установлена

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Список сайтов для проверки
sites = ['https://example.com', 'https://another-site.com']
active_users = set()

# Функция старта
async def start(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    active_users.add(user.id)
    await update.message.reply_text(f"Привет, {user.first_name}! Ты теперь можешь использовать команды /check и /stop.")

# Функция проверки сайтов
def check_sites() -> str:
    # Проверка сайтов
    down_sites = []
    for site in sites:
        # Пример логики для проверки сайта (замени на свою)
        site_is_up = True  # Для теста все сайты считаются рабочими
        if not site_is_up:
            down_sites.append(site)
    return down_sites

# Функция, которая отправляет сообщение о неработающих сайтах
async def check(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if user.id not in active_users:
        await update.message.reply_text("Ты не зарегистрирован для использования команд.")
        return

    await update.message.reply_text("Запуск проверки сайтов...")
    down_sites = check_sites()

    if down_sites:
        await update.message.reply_text(f"Не работают следующие сайты: {', '.join(down_sites)}")
    else:
        await update.message.reply_text("Все сайты работают!")

# Функция команды /stop
async def stop(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if user.id not in active_users:
        await update.message.reply_text("Ты не зарегистрирован для использования команд.")
        return

    await update.message.reply_text("Остановка проверки сайта...")

# Функция, которая будет выполняться каждый час
async def hourly_check(context: CallbackContext) -> None:
    down_sites = check_sites()
    if down_sites:
        for user_id in active_users:
            await context.bot.send_message(user_id, f"Не работают следующие сайты: {', '.join(down_sites)}")
    else:
        for user_id in active_users:
            await context.bot.send_message(user_id, "Все сайты работают!")

# Основная функция для настройки бота
async def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check", check))
    application.add_handler(CommandHandler("stop", stop))

    # Работает JobQueue для повторяющихся задач (например, ежечасная проверка)
    job_queue = application.job_queue

    # Настройка повторяющихся задач (каждый час в начале)
    now = datetime.now()
    # Следующий момент начала часа
    next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))

    # Запуск задачи в следующий час и каждый час после этого
    job_queue.run_repeating(hourly_check, interval=3600, first=next_hour)

    # Запуск бота
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
