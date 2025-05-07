import os
import logging
import asyncio
import nest_asyncio
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from datetime import datetime, timedelta

# Токен из переменной окружения
TOKEN = os.environ.get('8158547630:AAHXI6vOyekQ__paWkxPMMIzs-ho7A71LUs')

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Список сайтов для проверки
sites = ['https://example.com', 'https://another-site.com']
active_users = set()

# Функция старта
def start(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    active_users.add(user.id)
    update.message.reply_text(f"Привет, {user.first_name}! Ты теперь можешь использовать команды /check и /stop.")

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
def check(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if user.id not in active_users:
        update.message.reply_text("Ты не зарегистрирован для использования команд.")
        return

    update.message.reply_text("Запуск проверки сайтов...")
    down_sites = check_sites()

    if down_sites:
        update.message.reply_text(f"Не работают следующие сайты: {', '.join(down_sites)}")
    else:
        update.message.reply_text("Все сайты работают!")

# Функция команды /stop
def stop(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if user.id not in active_users:
        update.message.reply_text("Ты не зарегистрирован для использования команд.")
        return

    update.message.reply_text("Остановка проверки сайта...")

# Функция, которая будет выполняться каждый час
def hourly_check(context: CallbackContext):
    down_sites = check_sites()
    if down_sites:
        for user_id in active_users:
            context.bot.send_message(user_id, f"Не работают следующие сайты: {', '.join(down_sites)}")
    else:
        for user_id in active_users:
            context.bot.send_message(user_id, "Все сайты работают!")

# Основная функция для настройки бота
def main() -> None:
    """Запуск бота."""
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    # Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("check", check))
    dp.add_handler(CommandHandler("stop", stop))

    # Работает JobQueue для повторяющихся задач (например, ежечасная проверка)
    job_queue = updater.job_queue

    # Настройка повторяющихся задач (каждый час в начале)
    now = datetime.now()
    # Следующий момент начала часа
    next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))

    # Запуск задачи в следующий час
    job_queue.run_once(hourly_check, next_hour)

    # Запуск бота
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    nest_asyncio.apply()
    asyncio.run(main())
