import logging

import telebot

from config import TELEGRAM_TOKEN
from handlers import commands, photo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode=None)

commands.register(bot)
photo.register(bot)

if __name__ == "__main__":
    logging.getLogger(__name__).info("Bot started")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)
