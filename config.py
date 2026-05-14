import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN: str = os.environ["TELEGRAM_TOKEN"]
GEMINI_API_KEY: str = os.environ["GEMINI_API_KEY"]

_raw_ids = os.environ.get("ALLOWED_USER_IDS", "").strip()
ALLOWED_USER_IDS: set[int] = (
    {int(uid) for uid in _raw_ids.split(",") if uid.strip()}
    if _raw_ids
    else set()
)
