
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import REFERRAL_REWARD, SUPPORT_TELEGRAM, SUPPORT_EMAIL
from database import (
    register_user,
    get_user,
    get_wallet,
    get_packages,
    get_connection,
)
from keyboards import (
    main_menu,
    language_menu,
    payment_menu,
    package_menu,
)

FLOW_KEY = "payment_flow"


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_amount(value):
    value = value.translate(
        str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
    )
    value = value.replace(",", "").strip()

    if not re.fullmatch(r"\d+(?:\.\d{1,2})?", value):
        return None

    try:
        amount = Decimal(value)
    except InvalidOperation:
        return None

    if amount <= 0 or amount > Decimal("1000000"):
        return None

    return amount.quantize(Decimal("0.01"))


def find_package(package_id):
    for package in get_packages():
        if str(package["id"]) == str(package_id):
            return package
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user or not update.message:
        return

    context.user_data.pop(FLOW_KEY, None)
    context.user_data.pop("selected_package", None)
    context.user_data.pop("payment_purpose", None)

    is_new = register_user(
        user.id,
        user.username or "",
        user.full_name or "",
    )

    if is_new and context.args:
        try:
            referrer_id = int(context.args[0])

            if referrer_id != user.id:
                rewarded = False

                with get_connection() as db:
                    referrer = db.execute(
                        "SELECT user_id FROM users WHERE user_id = ?",
                        (referrer_id,),
                    ).fetchone()

                    if referrer:
                        db.execute(
                            """
                            UPDATE users
                            SET referral_count = referral_count + 1
                            WHERE user_id = ?
                            """,
                            (referrer_id,),
                        )

                        db.execute(
                            """
                            UPDATE wallets
                            SET referral_balance = referral_balance + ?
                            WHERE user_id = ?
                            """,
                            (REFERRAL_REWARD, referrer_id),
                        )

                        rewarded = True

                if rewarded:
                    from database import add_transaction

                    add_transaction(
                        referrer_id,
                        "referral",
                        REFERRAL_REWARD,
                        "approved",
                        f"Referral from {user.id}",
                    )

        except (ValueError, TypeError):
            pass

    await update.message.reply_text(
        "স্বাগতম AGAU PREMIUM BOT-এ!\n\n"
        "নিচের মেনু থেকে আপনার পছন্দের অপশন নির্বাচন করুন।",
        reply_markup=main_menu(),
    )


async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_wallet(update.effective_user.id)

    if not data:
        await update.message.reply_text("Wallet পাওয়া যায়নি।")
        return

    referral = Decimal(str(data["referral_balance"] or 0))
    deposit = Decimal(str(data["deposit_balance"] or 0))
    task = Decimal(str(data["task_balance"] or 0))
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

    total = Decimal("0")

    if wallet_data:
        total = (
            Decimal(str(wallet_data["referral_balance"] or 0))
            + Decimal(str(wallet_data["deposit_balance"] or 0))
            + Decimal(str(wallet_data["task_balance"] or 0))
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
        reply_markup=package_menu(packages),
    )


async def package_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    package_id = query.data.removeprefix("package_")
    package = find_package(package_id)

    if not package:
        await query.message.reply_text(
            "এই Package বর্তমানে পাওয়া যাচ্ছে না। আবার চেষ্টা করুন।"
        )
        return

    context.user_data["selected_package"] = str(package_id)
    context.user_data["payment_purpose"] = "premium"
    context.user_data.pop(FLOW_KEY, None)

    await query.message.reply_text(
        f"💎 Package: {package['name']}\n"
        f"💰 Price: {package['price']} TK\n\n"
        "Payment method নির্বাচন করুন:",
        reply_markup=payment_menu(),
    )


async def payment_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    method = query.data.removeprefix("payment_").upper()

    if method not in ("BKASH", "NAGAD"):
        await query.message.reply_text(
            "সঠিক Payment Method নির্বাচন করুন।"
        )
        return

    purpose = context.user_data.get("payment_purpose", "deposit")
    package_id = context.user_data.get("selected_package")

    package = None

    if purpose == "premium":
        package = find_package(package_id)

        if not package:
            context.user_data.pop("payment_purpose", None)
            context.user_data.pop("selected_package", None)

            await query.message.reply_text(
                "Package পাওয়া যায়নি। আবার চেষ্টা করুন।"
            )
            return

    context.user_data[FLOW_KEY] = {
        "step": "amount",
        "method": method,
        "purpose": purpose,
        "package_id": (
            str(package_id) if package_id is not None else None
        ),
    }

    if package:
        prompt = (
            f"💎 Package: {package['name']}\n"
            f"💰 নির্ধারিত মূল্য: {package['price']} TK\n\n"
            f"{method} দিয়ে Payment করার পর পাঠানো Amount লিখুন।"
        )
    else:
        prompt = (
            f"{method} দিয়ে Deposit করার পর কত TK পাঠিয়েছেন?\n\n"
            "শুধু Amount লিখুন। যেমন: 100"
        )

    await query.message.reply_text(prompt)


async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ভাষা নির্বাচন করুন:",
        reply_markup=language_menu(),
    )


async def language_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    lang = query.data.removeprefix("lang_")

    if lang not in ("bn", "en"):
        return

    with get_connection() as db:
        db.execute(
            "UPDATE users SET language = ? WHERE user_id = ?",
            (lang, query.from_user.id),
        )

    await query.message.reply_text(
        "ভাষা পরিবর্তন করা হয়েছে।" if lang == "bn"
        else "Language updated successfully.",
        reply_markup=main_menu(lang),
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
    message = "📞 SUPPORT\n\n"

    if SUPPORT_TELEGRAM:
        message += f"Telegram: {SUPPORT_TELEGRAM}\n"

    if SUPPORT_EMAIL:
        message += f"Email: {SUPPORT_EMAIL}\n"

    if message == "📞 SUPPORT\n\n":
        message += "Support contact এখনো সেট করা হয়নি।"

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
    with get_connection() as db:
        rows = db.execute(
            """
            SELECT type, amount, status, created_at
            FROM transactions
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
            """,
            (update.effective_user.id,),
        ).fetchall()

    if not rows:
        await update.message.reply_text(
            "📜 এখনো কোনো Transaction History নেই।"
        )
        return

    lines = ["📜 YOUR HISTORY\n"]

    for row in rows:
        lines.append(
            f"Type: {row['type']}\n"
            f"Amount: {row['amount']} TK\n"
            f"Status: {row['status']}\n"
            f"Date: {row['created_at']}\n"
        )

    await update.message.reply_text("\n".join(lines))


async def save_payment_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user_id = update.effective_user.id
    state = context.user_data.get(FLOW_KEY)

    if not state or state.get("step") != "screenshot":
        return

    if not update.message.photo:
        await update.message.reply_text(
            "Payment Screenshot ছবি হিসেবে পাঠান।"
        )
        return

    screenshot_id = update.message.photo[-1].file_id

    details = (
        f"Purpose: {state['purpose']}; "
        f"Method: {state['method']}; "
        f"Transaction ID: {state['transaction_id']}"
    )

    if state.get("package_id"):
        details += f"; Package ID: {state['package_id']}"

    try:
        with get_connection() as db:
            cursor = db.execute(
                """
                INSERT INTO deposits
                (user_id, method, amount, transaction_id,
                 screenshot_id, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    user_id,
                    state["method"],
                    float(state["amount"]),
                    state["transaction_id"],
                    screenshot_id,
                    now_iso(),
                ),
            )

            deposit_id = cursor.lastrowid

            db.execute(
                """
                INSERT INTO transactions
                (user_id, type, amount, status, details, created_at)
                VALUES (?, ?, ?, 'pending', ?, ?)
                """,
                (
                    user_id,
                    "premium_purchase"
                    if state["purpose"] == "premium" else "deposit",
                    float(state["amount"]),
                    details + f"; Deposit ID: {deposit_id}",
                    now_iso(),
                ),
            )

    except Exception:
        await update.message.reply_text(
            "❌ Request সংরক্ষণ করা যায়নি। পরে আবার চেষ্টা করুন।"
        )
        return

    context.user_data.pop(FLOW_KEY, None)
    context.user_data.pop("selected_package", None)
    context.user_data.pop("payment_purpose", None)

    await update.message.reply_text(
        "✅ আপনার Payment Request জমা হয়েছে।\n\n"
        f"💰 Amount: {Decimal(str(state['amount'])):.2f} TK\n"
        f"💳 Method: {state['method']}\n"
        "📌 Status: Pending Admin Verification\n\n"
        "Admin যাচাই না করা পর্যন্ত Balance বা Premium Active হবে না।",
        reply_markup=main_menu(),
    )


async def text_router(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    if not update.message or not update.message.text:
        return

    message_text = update.message.text.strip()
    state = context.user_data.get(FLOW_KEY)

    # Payment input is handled before menu buttons.
    if state:
        step = state.get("step")

        if step == "amount":
            amount = normalize_amount(message_text)

            if amount is None:
                await update.message.reply_text(
                    "❌ সঠিক Amount লিখুন। যেমন: 100"
                )
                return

            if state["purpose"] == "premium":
                package = find_package(state.get("package_id"))

                if not package:
                    context.user_data.pop(FLOW_KEY, None)
                    await update.message.reply_text(
                        "Package পাওয়া যাচ্ছে না। আবার নির্বাচন করুন।"
                    )
                    return

                try:
                    expected = Decimal(
                        str(package["price"])
                    ).quantize(Decimal("0.01"))
                except InvalidOperation:
                    await update.message.reply_text(
                        "Package-এর মূল্য সঠিকভাবে সেট করা নেই। Admin-এর সঙ্গে যোগাযোগ করুন।"
                    )
                    return

                if amount != expected:
                    await update.message.reply_text(
                        f"❌ সঠিক Amount লিখুন: {expected:.2f} TK"
                    )
                    return

            state["amount"] = str(amount)
            state["step"] = "transaction_id"

            await update.message.reply_text(
                "✅ Amount গ্রহণ করা হয়েছে।\n\n"
                "এখন Payment Transaction ID পাঠান।"
            )
            return

        if step == "transaction_id":
            transaction_id = message_text.strip()

            if not 4 <= len(transaction_id) <= 100:
                await update.message.reply_text(
                    "❌ সঠিক Transaction ID পাঠান।"
                )
                return

            state["transaction_id"] = transaction_id
            state["step"] = "screenshot"

            await update.message.reply_text(
                "এখন Payment Screenshot ছবি হিসেবে পাঠান।"
            )
            return

        if step == "screenshot":
            await update.message.reply_text(
                "আপনার Payment Screenshot ছবি হিসেবে পাঠান।"
            )
            return

    if message_text == "💰 My Wallet":
        await wallet(update, context)

    elif message_text == "👤 My Profile":
        await profile(update, context)

    elif message_text == "💎 Premium Membership":
        await premium(update, context)

    elif message_text == "👥 Referral":
        await referral(update, context)

    elif message_text == "📢 Notice":
        await notice(update, context)

    elif message_text == "📞 Support":
        await support(update, context)

    elif message_text == "🎯 Earn Money":
        await earn_money(update, context)

    elif message_text == "💸 Withdraw":
        await withdraw(update, context)

    elif message_text == "📜 History":
        await history(update, context)

    elif message_text in ("🌐 Language", "🌐 ভাষা পরিবর্তন"):
        await language(update, context)

    elif message_text == "📥 Deposit":
        context.user_data["payment_purpose"] = "deposit"
        context.user_data.pop("selected_package", None)
        context.user_data.pop(FLOW_KEY, None)

        await update.message.reply_text(
            "Deposit করতে bKash অথবা Nagad নির্বাচন করুন:",
            reply_markup=payment_menu(),
        )

    elif message_text in ("🔙 User Menu", "🔙 Back", "🔙 ফিরে যান"):
        context.user_data.pop(FLOW_KEY, None)

        await update.message.reply_text(
            "User Menu",
            reply_markup=main_menu(),
        )

    else:
        await update.message.reply_text(
            "নিচের Menu থেকে একটি অপশন নির্বাচন করুন।",
            reply_markup=main_menu(),
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
            save_payment_request
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router
        )
    )
