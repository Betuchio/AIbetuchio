"""Telegram ბოტის გაშვება."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.telegram.bot import create_bot
from src.data.db_manager import init_database
from src.utils.logger import get_logger

log = get_logger(__name__)


def main():
    log.info("=" * 60)
    log.info("AIbetuchio - Telegram Bot")
    log.info("=" * 60)

    init_database()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token or token == "your_token_here":
        log.error(
            "Telegram ტოკენი არ არის კონფიგურირებული!\n"
            "1. შექმენით ბოტი @BotFather-ში (/newbot)\n"
            "2. ტოკენი ჩაწერეთ .env ფაილში:\n"
            "   TELEGRAM_BOT_TOKEN=your_actual_token"
        )
        return

    log.info("ბოტი იწყებს მუშაობას...")
    bot = create_bot(token)
    bot.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
