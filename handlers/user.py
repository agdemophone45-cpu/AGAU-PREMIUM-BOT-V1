import re
from datetime import datetime

from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import REFERRAL_REWARD
from database import (
    register_user,
    get_user,
    get_wallet,
    get_packages,
    add_transaction,
)
from keyboards import (
    main_menu,
    language_menu,
    payment_menu,
    package_menu,
)

# Temporary input states
FLOW = {}


def normalize_amount(value):
    """Convert Bangla digits to English and validate amount."""
    value = value.translate(
        str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
    )
    value = value.replace(",", "").strip()

    if not re.fullmatch(r"\d+(\.\d{1,2})?", value):
        return None

    try:
        amount = float(value)
    except ValueError:
        return None

    if amount <= 0 or amount > 1000000:
        return None

    return amount


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user or not update.message:
        return

    FLOW.pop(user.id, None)

    is_new = register_user(
        user.id,
        user.username or "",
        user.full_name or ""
    )

    # Referral reward for a newly registered user
    if is_new and context.args:
        try:
            referrer_id = int(context.args[0])

            if referrer_id != user.id:
                from database import get_connection

                rewarded = False

                with get_connection() as db:
                    referrer = db.execute(
                        "SELECT user_id FROM users WHERE user_id = ?",
                        (referrer_id,)
                    ).fetchone()

                    if referrer:
                        db.execute("""
                            UPDATE users
                            SET referral_count = referral_count + 1
                            WHERE user_id = ?
                        """, (referrer_id,))

                        db.execute("""
                            UPDATE wallets
                            SET referral_balance =
                                referral_balance + ?
                            WHERE user_id = ?
                        """, (REFERRAL_REWARD, referrer_id))

                        rewarded = True

                if rewarded:
                    add_transaction(
                        referrer_id,
                        "referral",
                        REFERRAL_REWARD,
                        "approved",
                        f"Referral from {user.id}"
                    )

        except (ValueError, TypeError):
            pass

    await update.message.reply_text(
        "স্বাগতম AGAU PREMIUM BOT-এ!\n\n"
        "নিচের মেনু থেকে আপনার পছন্দের অপশন নির্বাচন করুন।",
        reply_markup=main_menu()
    )


async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = get_wallet(user_id)

    if not data:
        await update.message.reply_text("Wallet পাওয়া যায়নি।")
        return

    referral = data["referral_balance"]
    deposit = data["deposit_balance"]
    task = data["task_balance"]
    total = referral + deposit + task

    await update.message.reply_text(
        "💰 MY WALLET\n\n"
        f"👥 Referral Balance: {referral:.2f} TK\n"
        f"📥 Deposit Balance: {deposit:.2f} TK\n"
        f"🎯 Task Income: {task:.2f} TK\n\n"
        f"💎 Total Balance: {total:.2f} TK"
    )


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    wallet_data = get_wallet(user_id)

    if not user:
        await update.message.reply_text("Profile পাওয়া যায়নি।")
        return

    total = 0

    if wallet_data:
        total = (
            wallet_data["referral_balance"]
            + wallet_data["deposit_balance"]
            + wallet_data["task_balance"]
        )

    username = user["username"] or "N/A"

    await update.message.reply_text(
        "👤 MY PROFILE\n\n"
        f"Name: {user['full_name']}\n"
        f"Username: @{username}\n"
        f"Telegram ID: {user_id}\n"
        f"Referral Count: {user['referral_count']}\n"
        f"Premium: {user['premium_package'] or 'Not Active'}\n"
        f"Expiry: {user['premium_expiry'] or 'N/A'}\n"
        f"Total Balance: {total:.2f} TK"
    )


async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    packages = get_packages()

    if not packages:
        await update.message.reply_text(
            "এখন কোনো Premium Package পাওয়া যাচ্ছে না।"
        )
        return

    await update.message.reply_text(
        "💎 Premium Membership\n\n"
        "আপনার পছন্দের Package নির্বাচন করুন:",
        reply_markup=package_menu(packages)
    )


async def package_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    package_id = query.data.replace("package_", "")

    packages = get_packages()
    selected = next(
        (p for p in packages if str(p["id"]) == package_id),
        None
    )

    if not selected:
        await query.message.reply_text(
            "এই Package বর্তমানে পাওয়া যাচ্ছে না।"
        )
        return

    context.user_data["selected_package"] = package_id
    context.user_data["payment_purpose"] = "premium"

    await query.message.reply_text(
        f"💎 Package: {selected['name']}\n"
        f"💰 Price: {selected['price']} TK\n\n"
        "Payment method নির্বাচন করুন:",
        reply_markup=payment_menu()
    )


async def payment_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    method = query.data.replace("payment_", "").upper()

    if method not in ("BKASH", "NAGAD"):
        await query.message.reply_text("সঠিক Payment Method নির্বাচন করুন।")
        return

    purpose = context.user_data.get("payment_purpose", "deposit")

    FLOW[query.from_user.id] = {
        "step": "amount",
        "method": method,
        "purpose": purpose,
        "package_id": context.user_data.get("selected_package")
    }

    if purpose == "premium":
        packages = get_packages()
        package = next(
            (
                p for p in packages
                if str(p["id"]) == str(
                    context.user_data.get("selected_package")
                )
            ),
            None
        )

        if not package:
            FLOW.pop(query.from_user.id, None)
            await query.message.reply_text("Package পাওয়া যায়নি। আবার চেষ্টা করুন।")
            return

        await query.message.reply_text(
            f"💎 Package: {package['name']}\n"
            f"💰 নির্ধারিত মূল্য: {package['price']} TK\n\n"
            f"{method} দিয়ে Payment করার পর পাঠানো Amount লিখুন।"
        )
    else:
        await query.message.reply_text(
            f"{method} দিয়ে Deposit করার পর কত TK পাঠিয়েছেন?\n\n"
            "শুধু Amount লিখুন। যেমন: 100"
        )


async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ভাষা নির্বাচন করুন:",
        reply_markup=language_menu()
    )


async def language_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    lang = query.data.replace("lang_", "")

    from database import get_connection

    with get_connection() as db:
        db.execute(
            "UPDATE users SET language = ? WHERE user_id = ?",
            (lang, query.from_user.id)
        )

    await query.message.reply_text(
        "Language updated successfully.",
        reply_markup=main_menu(lang)
    )


async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot = await context.bot.get_me()
    link = f"https://t.me/{bot.username}?start={user_id}"

    await update.message.reply_text(
        "👥 YOUR REFERRAL LINK\n\n"
        f"{link}\n\n"
        f"প্রতি সফল Referral-এ Reward: {REFERRAL_REWARD} TK"
    )


async def notice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📢 কোনো নতুন Notice নেই।")


async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import SUPPORT_TELEGRAM, SUPPORT_EMAIL

    message = "📞 SUPPORT\n\n"

    if SUPPORT_TELEGRAM:
        message += f"Telegram: {SUPPORT_TELEGRAM}\n"

    if SUPPORT_EMAIL:
        message += f"Email: {SUPPORT_EMAIL}\n"

    await update.message.reply_text(message)


async def earn_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 Earn Money\n\n"
        "বর্তমানে Task System প্রস্তুত করা হচ্ছে।"
    )


async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💸 Withdrawal System\n\n"
        "Withdrawal Request System প্রস্তুত করা হচ্ছে।"
    )


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import get_connection

    user_id = update.effective_user.id

    with get_connection() as db:
        rows = db.execute("""
            SELECT type, amount, status, created_at
            FROM transactions
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
        """, (user_id,)).fetchall()

    if not rows:
        await update.message.reply_text(
            "📜 এখনো কোনো Transaction History নেই।"
        )
        return

    message = "📜 YOUR HISTORY\n\n"

    for row in rows:
        message += (
            f"Type: {row['type']}\n"
            f"Amount: {row['amount']} TK\n"
            f"Status: {row['status']}\n"
            f"Date: {row['created_at']}\n\n"
        )

    await update.message.reply_text(message)


async def deposit_screenshot(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user_id = update.effective_user.id
    state = FLOW.get(user_id)

    if not state or state.get("step") != "screenshot":
        return

    if not update.message.photo:
        await update.message.reply_text("Payment Screenshot ছবি হিসেবে পাঠান।")
        return

    screenshot_id = update.message.photo[-1].file_id
    amount = state["amount"]
    method = state["method"]
    transaction_id = state["transaction_id"]
    purpose = state["purpose"]
    package_id = state.get("package_id")

    details = (
        f"Purpose: {purpose}; Method: {method}; "
        f"Transaction ID: {transaction_id}"
    )

    if package_id:
        details += f"; Package ID: {package_id}"

    try:
        from database import get_connection

        with get_connection() as db:
            db.execute("""
                INSERT INTO deposits
                (user_id, method, amount, transaction_id,
                 screenshot_id, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """, (
                user_id,
                method,
                amount,
                transaction_id,
                screenshot_id,
                datetime.utcnow().isoformat()
            ))

            db.execute("""
                INSERT INTO transactions
                (user_id, type, amount, status, details, created_at)
                VALUES (?, ?, ?, 'pending', ?, ?)
            """, (
                user_id,
                "premium_purchase" if purpose == "premium" else "deposit",
                amount,
                details,
                datetime.utcnow().isoformat()
            ))

    except Exception:
        await update.message.reply_text(
            "❌ Request সংরক্ষণ করা যায়নি। পরে আবার চেষ্টা করুন।"
        )
        return

    FLOW.pop(user_id, None)

    context.user_data.pop("selected_package", None)
    context.user_data.pop("payment_purpose", None)

    await update.message.reply_text(
        "✅ আপনার Payment Request জমা হয়েছে।\n\n"
        f"💰 Amount: {amount:.2f} TK\n"
        f"💳 Method: {method}\n"
        f"📌 Status: Pending Admin Verification\n\n"
        "Admin যাচাই করার পর আপনাকে জানানো হবে।",
        reply_markup=main_menu()
    )


async def text_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    user_id = update.effective_user.id

    # Handle ongoing user input first
    state = FLOW.get(user_id)

    if state:
        step = state.get("step")

        if step == "amount":
            amount = normalize_amount(text)

            if amount is None:
                await update.message.reply_text(
                    "❌ সঠিক Amount লিখুন। যেমন: 100"
                )
                return

            # Premium package must be paid at its listed price
            if state["purpose"] == "premium":
                packages = get_packages()
                package = next(
                    (
                        p for p in packages
                        if str(p["id"]) == str(state.get("package_id"))
                    ),
                    None
                )

                if not package or round(amount, 2) != round(float(package["price"]), 2):
                    expected = package["price"] if package else "N/A"
                    await update.message.reply_text(
                        f"❌ Package-এর সঠিক Amount লিখুন: {expected} TK"
                    )
                    return

            state["amount"] = amount
            state["step"] = "transaction_id"

            await update.message.reply_text(
                "✅ Amount গ্রহণ করা হয়েছে।\n\n"
                "এখন Payment Transaction ID পাঠান।"
            )
            return

        if step == "transaction_id":
            transaction_id = text.strip()

            if len(transaction_id) < 4 or len(transaction_id) > 100:
                await update.message.reply_text(
                    "❌ সঠিক Transaction ID পাঠান।"
                )
                return

            state["transaction_id"] = transaction_id
            state["step"] = "screenshot"

            await update.message.reply_text(
                "এখন Payment Screenshot পাঠান।\n"
                "ছবি হিসেবে পাঠাবেন।"
            )
            return

        if step == "screenshot":
            await update.message.reply_text(
                "আপনার Payment Screenshot ছবি হিসেবে পাঠান।"
            )
            return

    # Main menu buttons
    if text == "💰 My Wallet":
        await wallet(update, context)

    elif text == "👤 My Profile":
        await profile(update, context)

    elif text == "💎 Premium Membership":
        await premium(update, context)

    elif text == "👥 Referral":
        await referral(update, context)

    elif text == "📢 Notice":
        await notice(update, context)

    elif text == "📞 Support":
        await support(update, context)

    elif text == "🎯 Earn Money":
        await earn_money(update, context)

    elif text == "💸 Withdraw":
        await withdraw(update, context)

    elif text == "📜 History":
        await history(update, context)

    elif text in ("🌐 Language", "🌐 ভাষা পরিবর্তন"):
        await language(update, context)

    elif text == "🔙 User Menu":
        await update.message.reply_text(
            "User Menu",
            reply_markup=main_menu()
        )

    elif text == "📥 Deposit":
        context.user_data["payment_purpose"] = "deposit"
        context.user_data.pop("selected_package", None)

        await update.message.reply_text(
            "Deposit করতে bKash অথবা Nagad নির্বাচন করুন:",
            reply_markup=payment_menu()
        )

    else:
        await update.message.reply_text(
            "নিচের Menu থেকে একটি অপশন নির্বাচন করুন।",
            reply_markup=main_menu()
        )


def register_user_handlers(application):

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CallbackQueryHandler(
            package_callback,
            pattern=r"^package_"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            payment_callback,
            pattern=r"^payment_"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            language_callback,
            pattern=r"^lang_"
        )
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            deposit_screenshot
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router
        )
    )
        await update.message.reply_text("Wallet পাওয়া যায়নি।")
        return

    referral = data["referral_balance"]
    deposit = data["deposit_balance"]
    task = data["task_balance"]

    total = referral + deposit + task

    await update.message.reply_text(
        "💰 MY WALLET\n\n"
        f"👥 Referral Balance: {referral:.2f} TK\n"
        f"📥 Deposit Balance: {deposit:.2f} TK\n"
        f"🎯 Task Income: {task:.2f} TK\n\n"
        f"💎 Total Balance: {total:.2f} TK"
    )


async def profile(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user_id = update.effective_user.id

    user = get_user(user_id)
    wallet_data = get_wallet(user_id)

    if not user:
        await update.message.reply_text("Profile পাওয়া যায়নি।")
        return

    total = 0

    if wallet_data:
        total = (
            wallet_data["referral_balance"]
            + wallet_data["deposit_balance"]
            + wallet_data["task_balance"]
        )

    await update.message.reply_text(
        "👤 MY PROFILE\n\n"
        f"Name: {user['full_name']}\n"
        f"Username: @{user['username']}\n"
        f"Telegram ID: {user_id}\n"
        f"Referral Count: {user['referral_count']}\n"
        f"Premium: {user['premium_package'] or 'Not Active'}\n"
        f"Expiry: {user['premium_expiry'] or 'N/A'}\n"
        f"Total Balance: {total:.2f} TK"
    )


async def premium(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    packages = get_packages()

    if not packages:
        await update.message.reply_text(
            "এখন কোনো Premium Package পাওয়া যাচ্ছে না।"
        )
        return

    await update.message.reply_text(
        "💎 Premium Membership\n\n"
        "আপনার পছন্দের Package নির্বাচন করুন:",
        reply_markup=package_menu(packages)
    )


async def package_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    package_id = query.data.replace("package_", "")

    context.user_data["selected_package"] = package_id

    await query.message.reply_text(
        "Package নির্বাচন করা হয়েছে।\n"
        "Payment method নির্বাচন করুন:",
        reply_markup=payment_menu()
    )


async def payment_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    method = query.data.replace("payment_", "").upper()

    context.user_data["deposit_method"] = method

    FLOW[query.from_user.id] = "deposit_amount"

    await query.message.reply_text(
        f"{method} দিয়ে Deposit করতে কত TK পাঠিয়েছেন?\n\n"
        "শুধু Amount লিখুন।"
    )


async def language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "ভাষা নির্বাচন করুন:",
        reply_markup=language_menu()
    )


async def language_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    lang = query.data.replace("lang_", "")

    from database import get_connection

    with get_connection() as db:
        db.execute(
            "UPDATE users SET language = ? WHERE user_id = ?",
            (lang, query.from_user.id)
        )

    await query.message.reply_text(
        "Language updated successfully.",
        reply_markup=main_menu(lang)
    )


async def referral(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user_id = update.effective_user.id

    bot = await context.bot.get_me()

    link = f"https://t.me/{bot.username}?start={user_id}"

    await update.message.reply_text(
        "👥 YOUR REFERRAL LINK\n\n"
        f"{link}\n\n"
        f"প্রতি সফল Referral-এ Reward: {REFERRAL_REWARD} TK"
    )


async def notice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "📢 কোনো নতুন Notice নেই।"
    )


async def support(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    from config import SUPPORT_TELEGRAM, SUPPORT_EMAIL

    message = "📞 SUPPORT\n\n"

    if SUPPORT_TELEGRAM:
        message += f"Telegram: {SUPPORT_TELEGRAM}\n"

    if SUPPORT_EMAIL:
        message += f"Email: {SUPPORT_EMAIL}\n"

    await update.message.reply_text(message)


async def earn_money(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🎯 Earn Money\n\n"
        "বর্তমানে Task System প্রস্তুত করা হচ্ছে।"
    )


async def withdraw(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "💸 Withdrawal System\n\n"
        "Withdrawal Request System প্রস্তুত করা হচ্ছে।"
    )


async def history(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    from database import get_connection

    user_id = update.effective_user.id

    with get_connection() as db:
        rows = db.execute("""
            SELECT type, amount, status, created_at
            FROM transactions
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
        """, (user_id,)).fetchall()

    if not rows:
        await update.message.reply_text(
            "📜 এখনো কোনো Transaction History নেই।"
        )
        return

    message = "📜 YOUR HISTORY\n\n"

    for row in rows:
        message += (
            f"Type: {row['type']}\n"
            f"Amount: {row['amount']} TK\n"
            f"Status: {row['status']}\n"
            f"Date: {row['created_at']}\n\n"
        )

    await update.message.reply_text(message)


async def text_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message or not update.message.text:
        return

    text = update.message.text

    if text == "💰 My Wallet":
        await wallet(update, context)

    elif text == "👤 My Profile":
        await profile(update, context)

    elif text == "💎 Premium Membership":
        await premium(update, context)

    elif text == "👥 Referral":
        await referral(update, context)

    elif text == "📢 Notice":
        await notice(update, context)

    elif text == "📞 Support":
        await support(update, context)

    elif text == "🎯 Earn Money":
        await earn_money(update, context)

    elif text == "💸 Withdraw":
        await withdraw(update, context)

    elif text == "📜 History":
        await history(update, context)

    elif text in ("🌐 Language", "🌐 ভাষা পরিবর্তন"):
        await language(update, context)

    elif text == "🔙 User Menu":
        await update.message.reply_text(
            "User Menu",
            reply_markup=main_menu()
        )

    elif text == "📥 Deposit":
        await update.message.reply_text(
            "Deposit করতে bKash অথবা Nagad নির্বাচন করুন:",
            reply_markup=payment_menu()
        )


def register_user_handlers(application):

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CallbackQueryHandler(
            package_callback,
            pattern=r"^package_"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            payment_callback,
            pattern=r"^payment_"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            language_callback,
            pattern=r"^lang_"
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router
        )
    )
