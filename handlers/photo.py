import logging
from datetime import date

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ALLOWED_USER_IDS
from models.invoice import Invoice
from services.gemini import recognize_invoice
from services.excel import generate_poster_excel

logger = logging.getLogger(__name__)

# In-memory store: message_id -> Invoice (cleared on new photo)
_pending: dict[int, Invoice] = {}


def _is_allowed(user_id: int) -> bool:
    return not ALLOWED_USER_IDS or user_id in ALLOWED_USER_IDS


def _build_preview(invoice: Invoice) -> str:
    header = f"{'Товар':<30} {'К-сть':>8} {'Ціна':>8} {'Сума':>10}"
    sep = "─" * len(header)
    lines = [header, sep]
    grand_total = 0.0
    for item in invoice.items:
        qty_str = f"{item.quantity:g} {item.unit}"
        row = f"{item.name[:30]:<30} {qty_str:>8} {item.price_per_unit:>8.2f} {item.total:>10.2f}"
        lines.append(row)
        grand_total += item.total
    lines.append(sep)
    lines.append(f"РАЗОМ: {grand_total:.2f} грн")
    return "```\n" + "\n".join(lines) + "\n```"


def _confirm_markup(chat_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("✅ Завантажити Excel", callback_data=f"excel:{chat_id}"),
        InlineKeyboardButton("❌ Скасувати", callback_data=f"cancel:{chat_id}"),
    )
    return kb


def register(bot: telebot.TeleBot) -> None:

    def _handle_image(message: telebot.types.Message, file_id: str) -> None:
        if not _is_allowed(message.from_user.id):
            bot.send_message(message.chat.id, "У вас немає доступу до цього бота.")
            return

        status = bot.send_message(message.chat.id, "⏳ Розпізнаю накладну...")

        try:
            file_info = bot.get_file(file_id)
            image_bytes = bot.download_file(file_info.file_path)
            invoice = recognize_invoice(image_bytes)
        except Exception as e:
            logger.exception("Помилка розпізнавання")
            bot.edit_message_text(
                f"Помилка розпізнавання: {e}",
                chat_id=message.chat.id,
                message_id=status.message_id,
            )
            return

        if not invoice.items:
            bot.edit_message_text(
                "Не вдалося знайти товари на фото. Спробуйте чіткіше фото накладної.",
                chat_id=message.chat.id,
                message_id=status.message_id,
            )
            return

        _pending[message.chat.id] = invoice

        preview = _build_preview(invoice)
        bot.edit_message_text(
            f"Розпізнано {len(invoice.items)} позицій:\n\n{preview}",
            chat_id=message.chat.id,
            message_id=status.message_id,
            parse_mode="Markdown",
            reply_markup=_confirm_markup(message.chat.id),
        )

    @bot.message_handler(content_types=["photo"])
    def on_photo(message: telebot.types.Message) -> None:
        largest = max(message.photo, key=lambda p: p.file_size)
        _handle_image(message, largest.file_id)

    @bot.message_handler(content_types=["document"])
    def on_document(message: telebot.types.Message) -> None:
        doc = message.document
        mime = doc.mime_type or ""
        if not mime.startswith("image/"):
            bot.send_message(
                message.chat.id,
                "Надішліть фото або зображення (jpg/png). PDF поки що не підтримується.",
            )
            return
        _handle_image(message, doc.file_id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("excel:"))
    def on_excel(call: telebot.types.CallbackQuery) -> None:
        chat_id = int(call.data.split(":")[1])
        invoice = _pending.get(chat_id)
        if not invoice:
            bot.answer_callback_query(call.id, "Дані вже не актуальні. Надішліть фото знову.")
            return

        bot.answer_callback_query(call.id, "Генерую Excel...")
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None,
        )

        try:
            filename = f"supply_{date.today().isoformat()}.xlsx"
            excel_bytes = generate_poster_excel(invoice, filename)
            bot.send_document(
                chat_id,
                (filename, excel_bytes),
                caption=f"Excel для імпорту в Poster POS — {len(invoice.items)} позицій",
            )
        except Exception as e:
            logger.exception("Помилка генерації Excel")
            bot.send_message(chat_id, f"Помилка генерації Excel: {e}")

        _pending.pop(chat_id, None)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("cancel:"))
    def on_cancel(call: telebot.types.CallbackQuery) -> None:
        chat_id = int(call.data.split(":")[1])
        _pending.pop(chat_id, None)
        bot.answer_callback_query(call.id)
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None,
        )
        bot.send_message(chat_id, "Скасовано.")
