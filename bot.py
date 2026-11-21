
import logging
import sys

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
)

from config import BOT_TOKEN
from database import init_db
from handlers.user import register_user_handlers
from handlers.admin import register_admin_handlers


# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle unexpected bot errors."""
    logger.error(
        "An error occurred while processing an update:",
        exc_info=context.error
    )


def main() -> None:
    """Start AGAU PREMIUM BOT."""

    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN is missing.")
        sys.exit(1)

    # Initialize database
    init_db()

    # Create Telegram application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Register user commands and buttons
    register_user_handlers(application)

    # Register admin commands and buttons
    register_admin_handlers(application)

    # Register error handler
    application.add_error_handler(error_handler)

    logger.info("AGAU PREMIUM BOT is starting...")

    # Start polling
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
