import json
import re

from google import genai
from google.genai import types

from config import GEMINI_API_KEY
from models.invoice import Invoice, InvoiceItem

_client = genai.Client(api_key=GEMINI_API_KEY)

_PROMPT = """
Ти OCR-асистент для розпізнавання накладних постачальників.
Проаналізуй фото накладної і поверни ТІЛЬКИ JSON масив товарів без жодних пояснень.

Формат:
[
  {
    "name": "Назва товару як написано в накладній",
    "quantity": 10.0,
    "unit": "кг",
    "price_per_unit": 45.50,
    "total": 455.00
  }
]

Правила:
- Якщо price_per_unit відсутня — вирахуй з total / quantity
- Якщо total відсутній — вирахуй з price_per_unit * quantity
- unit: кг / л / шт / г / мл (визнач з контексту)
- Числа — тільки float без символів валюти
- Якщо поле нерозбірливе — залиш розумне значення за замовчуванням
""".strip()


def _extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        return match.group(1).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        return text[start : end + 1]
    raise ValueError(f"JSON не знайдено у відповіді:\n{text}")


def recognize_invoice(image_bytes: bytes) -> Invoice:
    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
    response = _client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=[_PROMPT, image_part],
    )
    raw_text = response.text

    json_str = _extract_json(raw_text)
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Не вдалося розпарсити JSON: {e}\n\nВідповідь:\n{raw_text}")

    items = []
    for row in data:
        qty = float(row.get("quantity") or 0)
        price = float(row.get("price_per_unit") or 0)
        total = float(row.get("total") or 0)

        if price and not total and qty:
            total = round(price * qty, 2)
        elif total and not price and qty:
            price = round(total / qty, 2)

        items.append(
            InvoiceItem(
                name=str(row.get("name", "")).strip(),
                quantity=qty,
                unit=str(row.get("unit", "шт")).strip(),
                price_per_unit=price,
                total=total,
            )
        )

    return Invoice(items=items, raw_text=raw_text)
