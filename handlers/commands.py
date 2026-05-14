import telebot

_START_TEXT = (
    "Привіт! Я допоможу перенести накладну в Poster POS.\n\n"
    "Надішліть фото накладної, і я згенерую Excel файл для імпорту.\n\n"
    "Підтримуються: фото, документи (jpg, png).\n"
    "PDF поки що не підтримується."
)

_HELP_TEXT = (
    "Як користуватись:\n"
    "1. Сфотографуйте накладну від постачальника\n"
    "2. Надішліть фото в цей чат\n"
    "3. Перевірте розпізнані дані\n"
    "4. Натисніть ✅ Завантажити Excel\n"
    "5. Імпортуйте файл у Poster POS (Склад → Постачання → Імпорт)"
)


def register(bot: telebot.TeleBot) -> None:
    @bot.message_handler(commands=["start"])
    def cmd_start(message: telebot.types.Message) -> None:
        bot.send_message(message.chat.id, _START_TEXT)

    @bot.message_handler(commands=["help"])
    def cmd_help(message: telebot.types.Message) -> None:
        bot.send_message(message.chat.id, _HELP_TEXT)
