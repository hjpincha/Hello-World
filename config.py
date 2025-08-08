from pathlib import Path
import os

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PIPELINE_DIR = BASE_DIR / "pipelines"

# OpenAI configuration
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Trading constants
POSITION_SIZE = 0.05  # 5% of equity per position
TAKE_PROFIT = 0.15
STOP_LOSS = -0.10
MAX_HOLD_DAYS = 10
COOL_OFF_DAYS = 5

# Misc
DATE_FORMAT = "%Y-%m-%d"
