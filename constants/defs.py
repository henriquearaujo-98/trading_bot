import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_KEY = os.environ.get("OANDA_API_KEY")
ACCOUNT_ID = os.environ.get("OANDA_ACCOUNT_ID")
OANDA_URL = os.environ.get("OANDA_URL", "https://api-fxpractice.oanda.com/v3")

if not API_KEY or not ACCOUNT_ID:
    raise RuntimeError(
        "Missing OANDA credentials. Copy .env.example to .env and set "
        "OANDA_API_KEY and OANDA_ACCOUNT_ID."
    )

SELL = -1
BUY = 1
NONE = 0

OPEN = 1
CLOSE = -1
