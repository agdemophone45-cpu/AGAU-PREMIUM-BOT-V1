
from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import ADMIN_IDS
from database import get_connection
from keyboards import admin_menu, main_menu


def is_admin(user_id):
    return user_id in ADMIN_IDS


async def admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Access Denied.")
        return

    await update.message.reply_text(
        "🔐 AGAU PREMIUM BOT ADMIN PANEL\n\n"
        "Owner Access Granted.",
        reply_markup=admin_menu(),
    )


async def dashboard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
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
            """
            SELECT COUNT(*) FROM deposits
            WHERE status = 'pending'
            """
        ).fetchone()[0]

        withdrawals = db.execute(
            """
            SELECT COUNT(*) FROM withdrawals
            WHERE status = 'pending'
            """
        ).fetchone()[0]

        tasks = db.execute(
            """
            SELECT COUNT(*) FROM task_submissions
            WHERE status = 'pending'
            """
        ).fetchone()[0]

    await update.message.reply_text(
        "📊 ADMIN DASHBOARD\n\n"
        f"👥 Total Users: {users}\n"
        f"🚫 Banned Users: {banned}\n"
        f"💎 Premium Users: {premium}\n"
        f"📥 Pending Deposits: {deposits}\n"
        f"💸 Pending Withdrawals: {withdrawals}\n"
        f"🎯 Pending Tasks: {tasks}"
    )


async def manage_users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["admin_action"] = "search_user"

    await update.message.reply_text(
        "👥 USER MANAGEMENT\n\n"
        "ব্যবহারকারীর Telegram ID লিখুন:"
    )


async def show_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    target_id: int,
):
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
        await update.message.reply_text(
            "এই User পাওয়া যায়নি।"
        )
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


async def search_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if context.user_data.get("admin_action") != "search_user":
        return

    if not update.message or not update.message.text:
        return

    try:
        target_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "সঠিক Telegram ID লিখুন।"
        )
        return

    context.user_data.pop("admin_action", None)

    await show_user(update, context, target_id)


async def pending_deposits(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    with get_connection() as db:
        rows = db.execute(
            """
            SELECT * FROM deposits
            WHERE status = 'pending'
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()

    if not rows:
        await update.message.reply_text(
            "কোনো Pending Deposit নেই।"
        )
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


async def pending_withdrawals(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    with get_connection() as db:
        rows = db.execute(
            """
            SELECT * FROM withdrawals
            WHERE status = 'pending'
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()

    if not rows:
        await update.message.reply_text(
            "কোনো Pending Withdrawal নেই।"
        )
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


async def admin_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id

    if not is_admin(user_id):
        return

    text = update.message.text.strip()

    # Pending user search has priority over menu routing.
    if context.user_data.get("admin_action") == "search_user":
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

    elif text == "🔙 User Menu":
        context.user_data.clear()
        await update.message.reply_text(
            "User Menu",
            reply_markup=main_menu(),
        )

    elif text == "💎 Packages":
        await update.message.reply_text(
            "Package Management এখনো তৈরি হয়নি।"
        )

    elif text == "💳 Payment Settings":
        await update.message.reply_text(
            "Payment Settings এখনো তৈরি হয়নি।"
        )

    elif text == "🎯 Task Management":
        await update.message.reply_text(
            "Task Management এখনো তৈরি হয়নি।"
        )

    elif text == "📢 Broadcast":
        await update.message.reply_text(
            "Broadcast System এখনো তৈরি হয়নি।"
        )

    elif text == "📞 Support Settings":
        await update.message.reply_text(
            "Support Settings এখনো তৈরি হয়নি।"
        )

    elif text == "⚙️ Settings":
        await update.message.reply_text(
            "Settings এখনো তৈরি হয়নি।"
        )

    elif text == "👨‍💼 Job Admin":
        await update.message.reply_text(
            "Job Admin Management এখনো তৈরি হয়নি।"
        )

    elif text == "📜 Admin Logs":
        await update.message.reply_text(
            "Admin Logs এখনো তৈরি হয়নি।"
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
