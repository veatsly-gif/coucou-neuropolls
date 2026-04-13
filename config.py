"""Environment and paths for the bot."""

import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN: str | None = os.getenv("TELEGRAM_TOKEN")
DATA_DIR: str = os.getenv("DATA_DIR", "data")
TRAINING_FILENAME: str = os.getenv("TRAINING_FILENAME", "training_data.txt")
TRAINING_PATH: str = os.path.join(DATA_DIR, TRAINING_FILENAME)

# Telegram poll limits (Bot API)
MAX_QUESTION_LEN: int = int(os.getenv("MAX_QUESTION_LEN", "300"))
MAX_OPTION_LEN: int = int(os.getenv("MAX_OPTION_LEN", "100"))
