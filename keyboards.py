
from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


# Main user menu
def main_menu(language="bn"):
    if language == "en":
        buttons = [
            ["💎 Premium Membership", "💰 My Wallet"],
            ["📥 Deposit", "🎯 Earn Money"],
            ["💸 Withdraw", "👥 Referral"],
            ["👤 My Profile", "📜 History"],
            ["📢 Notice", "📞 Support"],
            ["🌐 Language"],
        ]
    else:
        buttons = [
            ["💎 Premium Membership", "💰 My Wallet"],
            ["📥 Deposit", "🎯 Earn Money"],
            ["💸 Withdraw", "👥 Referral"],
            ["👤 My Profile", "📜 History"],
            ["📢 Notice", "📞 Support"],
            ["🌐 ভাষা পরিবর্তন"],
        ]

    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
        is_persistent=True,
    )


# Language selection
def language_menu():
    buttons = [
        [
            InlineKeyboardButton(
                "🇧🇩 বাংলা",
                callback_data="lang_bn",
            ),
            InlineKeyboardButton(
                "🇬🇧 English",
                callback_data="lang_en",
            ),
        ]
    ]

    return InlineKeyboardMarkup(buttons)


# Admin main menu
def admin_menu():
    buttons = [
        ["📊 Dashboard", "👥 Manage Users"],
        ["💎 Packages", "💳 Payment Settings"],
        ["🎯 Task Management", "💸 Withdraw Requests"],
        ["📥 Deposit Requests", "📢 Broadcast"],
        ["📞 Support Settings", "⚙️ Settings"],
        ["👨‍💼 Job Admin", "📜 Admin Logs"],
        ["🔙 User Menu"],
    ]

    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
        is_persistent=True,
    )


# Back button
def back_menu(language="bn"):
    text = "🔙 Back" if language == "en" else "🔙 ফিরে যান"

    return ReplyKeyboardMarkup(
        [[text]],
        resize_keyboard=True,
    )


# Payment method selection
def payment_menu():
    buttons = [
        [
            InlineKeyboardButton(
                "bKash",
                callback_data="payment_bkash",
            ),
            InlineKeyboardButton(
                "Nagad",
                callback_data="payment_nagad",
            ),
        ]
    ]

    return InlineKeyboardMarkup(buttons)


# Admin approve/reject buttons
def review_menu(item_type, item_id):
    buttons = [
        [
            InlineKeyboardButton(
                "✅ Approve",
                callback_data=f"{item_type}_approve_{item_id}",
            ),
            InlineKeyboardButton(
                "❌ Reject",
                callback_data=f"{item_type}_reject_{item_id}",
            ),
        ]
    ]

    return InlineKeyboardMarkup(buttons)


# Premium package buttons
def package_menu(packages):
    buttons = []

    for package in packages:
        if not package.get("active", 1):
            continue

        buttons.append([
            InlineKeyboardButton(
                f"{package['name']} - {package['price']} TK",
                callback_data=f"package_{package['id']}",
            )
        ])

    return InlineKeyboardMarkup(buttons)


# Confirmation buttons
def confirm_menu(action, item_id):
    buttons = [
        [
            InlineKeyboardButton(
                "✅ Confirm",
                callback_data=f"{action}_confirm_{item_id}",
            ),
            InlineKeyboardButton(
                "❌ Cancel",
                callback_data=f"{action}_cancel_{item_id}",
            ),
        ]
    ]

    return InlineKeyboardMarkup(buttons)


# Job Admin application review
def job_admin_review_menu(application_id):
    buttons = [
        [
            InlineKeyboardButton(
                "✅ Approve",
                callback_data=f"job_approve_{application_id}",
            ),
            InlineKeyboardButton(
                "❌ Reject",
                callback_data=f"job_reject_{application_id}",
            ),
        ]
    ]

    return InlineKeyboardMarkup(buttons)


# Job Admin permission options
def job_admin_permission_menu(user_id):
    buttons = [
        [
            InlineKeyboardButton(
                "🔐 Set Permissions",
                callback_data=f"job_permissions_{user_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "🚫 Disable Job Admin",
                callback_data=f"job_disable_{user_id}",
            )
        ],
    ]

    return InlineKeyboardMarkup(buttons)
