
import os

# Telegram Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Admin Configuration
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Admin Security
ADMIN_PIN = os.getenv("ADMIN_PIN", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# Database Configuration
DB_PATH = os.getenv("DB_PATH", "data/agau.db")

# Support Configuration
SUPPORT_TELEGRAM = os.getenv(
    "SUPPORT_TELEGRAM",
    "@ag_support_bd"
)

SUPPORT_EMAIL = os.getenv(
    "SUPPORT_EMAIL",
    ""
)

# Payment Configuration
BKASH_NUMBER = os.getenv("BKASH_NUMBER", "")
NAGAD_NUMBER = os.getenv("NAGAD_NUMBER", "")

# Default Premium Packages
DEFAULT_PACKAGES = [
    {
        "name": "1 DAY",
        "duration_days": 1,
        "price": 4
    },
    {
        "name": "7 DAY",
        "duration_days": 7,
        "price": 25
    },
    {
        "name": "30 DAY",
        "duration_days": 30,
        "price": 100
    },
    {
        "name": "3 MONTHS",
        "duration_days": 90,
        "price": 248
    },
    {
        "name": "1 YEAR",
        "duration_days": 365,
        "price": 1000
    },
    {
        "name": "LIFETIME",
        "duration_days": 0,
        "price": 5000
    }
]

# Referral Configuration
REFERRAL_REWARD = 5

# Language Configuration
DEFAULT_LANGUAGE = "bn"
SUPPORTED_LANGUAGES = ["bn", "en"]

# Withdrawal Configuration
MIN_WITHDRAW = int(os.getenv("MIN_WITHDRAW", "0"))

# Deposit Configuration
MIN_DEPOSIT = int(os.getenv("MIN_DEPOSIT", "0"))

# Task Configuration
TASK_REVIEW_MINUTES = 180
