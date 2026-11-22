
import logging

from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import ADMIN_IDS
from database import get_connection, add_admin_log
from keyboards import admin_menu, main_menu

logger = logging.getLogger(__name__)


def is_admin(user_id):
    return user_id in ADMIN_IDS


def log_action(admin_id, action, target_user=None, reason=None):
    try:
        add_admin_log(
            admin_id=admin_id,
            action=action,
            target_user=target_user,
            reason=reason or "",
        )
    except Exception:
        logger.exception("Failed to save admin activity log")


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("Access Denied.")
        return

    context.user_data.clear()
    context.user_data["admin_mode"] = True

    log_action(user_id, "Opened Admin Panel")

    await update.message.reply_text(
        "🔐 AGAU PREMIUM BOT ADMIN PANEL\n\n"
        "Owner Access Granted.",
        reply_markup=admin_menu(),
    )


async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_connection() as db:
        users = db.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        banned = db.execute(
            "SELECT COUNT(*) FROM users WHERE is_banned = 1"
        ).fetchone()[0]

        premium = db.execute(
            """
            SELECT COUNT(*) FROM users
            WHERE premium_package IS NOT NULL
            """
        ).fetchone()[0]

        deposits = db.execute(
            "SELECT COUNT(*) FROM deposits WHERE status = 'pending'"
        ).fetchone()[0]

        withdrawals = db.execute(
            "SELECT COUNT(*) FROM withdrawals WHERE status = 'pending'"
        ).fetchone()[0]

        tasks = db.execute(
            """
            SELECT COUNT(*) FROM task_submissions
            WHERE status = 'pending'
            """
        ).fetchone()[0]

        applications = db.execute(
            """
            SELECT COUNT(*) FROM job_admin_applications
            WHERE status = 'pending'
            """
        ).fetchone()[0]

    log_action(update.effective_user.id, "Viewed Dashboard")

    await update.message.reply_text(
        "📊 ADMIN DASHBOARD\n\n"
        f"👥 Total Users: {users}\n"
        f"🚫 Banned Users: {banned}\n"
        f"💎 Premium Users: {premium}\n"
        f"📥 Pending Deposits: {deposits}\n"
        f"💸 Pending Withdrawals: {withdrawals}\n"
        f"🎯 Pending Tasks: {tasks}\n"
        f"👨‍💼 Job Admin Applications: {applications}"
    )


async def manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_action"] = "search_user"

    log_action(update.effective_user.id, "Opened User Management")

    await update.message.reply_text(
        "👥 USER MANAGEMENT\n\n"
        "ব্যবহারকারীর Telegram ID লিখুন:"
    )


async def show_user(update: Update, target_id: int):
    with get_connection() as db:
        user = db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (target_id,),
        ).fetchone()

        wallet = db.execute(
            "SELECT * FROM wallets WHERE user_id = ?",
            (target_id,),
        ).fetchone()

    if not user:
        await update.message.reply_text("এই User পাওয়া যায়নি।")
        return

    balance_text = "Wallet পাওয়া যায়নি।"

    if wallet:
        referral = float(wallet["referral_balance"] or 0)
        deposit = float(wallet["deposit_balance"] or 0)
        task = float(wallet["task_balance"] or 0)

        balance_text = (
            f"Referral: {referral:.2f} TK\n"
            f"Deposit: {deposit:.2f} TK\n"
            f"Task: {task:.2f} TK\n"
            f"Total: {referral + deposit + task:.2f} TK"
        )

    await update.message.reply_text(
        "👤 USER DETAILS\n\n"
        f"Name: {user['full_name'] or 'N/A'}\n"
        f"Username: @{user['username'] or 'N/A'}\n"
        f"ID: {user['user_id']}\n"
        f"Joined: {user['join_date']}\n"
        f"Last Active: {user['last_active']}\n"
        f"Referral Count: {user['referral_count']}\n"
        f"Premium: {user['premium_package'] or 'Not Active'}\n"
        f"Expiry: {user['premium_expiry'] or 'N/A'}\n"
        f"Banned: {bool(user['is_banned'])}\n\n"
        f"💰 WALLET\n{balance_text}"
    )


async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target_id = int(update.message.text.strip())

        if target_id <= 0:
            raise ValueError

    except (ValueError, TypeError):
        await update.message.reply_text("সঠিক Telegram ID লিখুন।")
        return

    context.user_data.pop("admin_action", None)

    log_action(
        update.effective_user.id,
        "Viewed User Details",
        target_user=target_id,
    )

    await show_user(update, target_id)


async def pending_deposits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_connection() as db:
        rows = db.execute(
            """
            SELECT * FROM deposits
            WHERE status = 'pending'
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()

    log_action(update.effective_user.id, "Viewed Pending Deposits")

    if not rows:
        await update.message.reply_text("কোনো Pending Deposit নেই।")
        return

    for row in rows:
        await update.message.reply_text(
            "📥 PENDING DEPOSIT\n\n"
            f"Request ID: {row['id']}\n"
            f"User ID: {row['user_id']}\n"
            f"Method: {row['method']}\n"
            f"Amount: {row['amount']} TK\n"
            f"Status: {row['status']}"
        )


async def pending_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_connection() as db:
        rows = db.execute(
            """
            SELECT * FROM withdrawals
            WHERE status = 'pending'
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()

    log_action(update.effective_user.id, "Viewed Pending Withdrawals")

    if not rows:
        await update.message.reply_text("কোনো Pending Withdrawal নেই।")
        return

    for row in rows:
        await update.message.reply_text(
            "💸 PENDING WITHDRAWAL\n\n"
            f"Request ID: {row['id']}\n"
            f"User ID: {row['user_id']}\n"
            f"Method: {row['method']}\n"
            f"Amount: {row['amount']} TK\n"
            f"Status: {row['status']}"
        )


async def show_admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with get_connection() as db:
        rows = db.execute(
            """
            SELECT admin_id, action, target_user, reason, created_at
            FROM admin_logs
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()

    if not rows:
        await update.message.reply_text(
            "এখনো কোনো Admin Activity Log নেই।"
        )
        return

    for row in rows:
        await update.message.reply_text(
            "📜 ADMIN ACTIVITY\n\n"
            f"Owner ID: {row['admin_id']}\n"
            f"Action: {row['action']}\n"
            f"Target: {row['target_user'] or 'N/A'}\n"
            f"Reason: {row['reason'] or 'N/A'}\n"
            f"Date: {row['created_at']}"
        )


async def admin_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    if not update.effective_user:
        return

    user_id = update.effective_user.id

    if not is_admin(user_id):
        return

    if not context.user_data.get("admin_mode"):
        return

    text = update.message.text.strip()

    if context.user_data.get("admin_action") == "search_user":
        if text == "🔙 User Menu":
            context.user_data.clear()
            await update.message.reply_text(
                "User Menu",
                reply_markup=main_menu(),
            )
            return

        await search_user(update, context)
        return

    if text == "📊 Dashboard":
        await dashboard(update, context)

    elif text == "👥 Manage Users":
        await manage_users(update, context)

    elif text == "📥 Deposit Requests":
        await pending_deposits(update, context)

    elif text == "💸 Withdraw Requests":
        await pending_withdrawals(update, context)

    elif text == "📜 Admin Logs":
        await show_admin_logs(update, context)

    elif text == "🔙 User Menu":
        context.user_data.clear()

        log_action(user_id, "Returned to User Menu")

        await update.message.reply_text(
            "User Menu",
            reply_markup=main_menu(),
        )

    elif text in (
        "💎 Packages",
        "💳 Payment Settings",
        "🎯 Task Management",
        "📢 Broadcast",
        "📞 Support Settings",
        "⚙️ Settings",
        "👨‍💼 Job Admin",
    ):
        await update.message.reply_text(
            "এই বিভাগটি এখনো তৈরি করা হয়নি।"
        )


def register_admin_handlers(application):
    application.add_handler(
        CommandHandler("admin", admin_command)
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            admin_router,
        ),
        group=1,
    )
