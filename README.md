
# AGAU PREMIUM BOT

Telegram Premium Membership and Earning Bot.

## Features

- Bengali and English language menu
- Premium membership packages
- Three separate wallet balances
- Referral system
- Deposit and withdrawal database
- Task management database
- User profile and transaction history
- Admin dashboard
- SQLite database

## Default Premium Packages

| Package | Price |
|---|---:|
| 1 DAY | 4 TK |
| 7 DAY | 25 TK |
| 30 DAY | 100 TK |
| 3 MONTHS | 248 TK |
| 1 YEAR | 1000 TK |
| LIFETIME | 5000 TK |

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

Configure these variables in your hosting dashboard:

- BOT_TOKEN
- ADMIN_ID
- ADMIN_PIN
- ADMIN_PASSWORD
- DB_PATH
- BKASH_NUMBER
- NAGAD_NUMBER
- MIN_DEPOSIT
- MIN_WITHDRAW
- SUPPORT_TELEGRAM
- SUPPORT_EMAIL

## Start Bot

```bash
python bot.py
```

## Hosting

The project is intended to run as a Python worker on FadeHost.

Configure all secret values through the hosting environment settings.

## Database

SQLite is used for storing users, wallets, packages, transactions, deposits, withdrawals and tasks.

Make sure the hosting platform provides persistent storage.

## Important Notice

This repository currently contains a starter implementation.

Deposit verification, withdrawal processing, task approval, premium activation, channel invitations, admin security and several management features still require implementation and testing.

Do not use this starter version for real-money transactions.
