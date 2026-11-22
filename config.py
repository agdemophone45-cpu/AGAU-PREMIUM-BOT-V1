
import os

# Telegram Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Admin Configuration
ADMIN_IDS = (6597366825, 6650444747)

# Backward compatibility with older code
ADMIN_ID = ADMIN_IDS[0]

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
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "")

# Payment Configuration
# Financial settings should be configured and managed
# by a responsible adult owner.
BKASH_NUMBER = os.getenv("BKASH_NUMBER", "")
NAGAD_NUMBER = os.getenv("NAGAD_NUMBER", "")

# Default Premium Packages
DEFAULT_PACKAGES = [
    {
        "name": "5 DAY",
        "duration_days": 5,
        "price": 7,
        "active": True
    },
    {
        "name": "7 DAY",
        "duration_days": 7,
        "price": 10,
        "active": True
    },
    {
        "name": "30 DAY",
        "duration_days": 30,
        "price": 44,
        "active": True
    },
    {
        "name": "3 MONTHS",
        "duration_days": 90,
        "price": 120,
        "active": True
    },
    {
        "name": "1 YEAR",
        "duration_days": 365,
        "price": 500,
        "active": True
    },
    {
        "name": "LIFETIME",
        "duration_days": 0,
        "price": 0,
        "active": False
    }
]

# Referral Configuration
REFERRAL_REWARD = 1

# Language Configuration
DEFAULT_LANGUAGE = "bn"
SUPPORTED_LANGUAGES = ["bn", "en"]

# Withdrawal Configuration
MIN_WITHDRAW = int(os.getenv("MIN_WITHDRAW", "0"))

# Deposit Configuration
MIN_DEPOSIT = int(os.getenv("MIN_DEPOSIT", "0"))

# Task Configuration
TASK_REVIEW_MINUTES = 180
