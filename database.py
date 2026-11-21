
import os
import sqlite3
from datetime import datetime

from config import DB_PATH, DEFAULT_PACKAGES


def get_connection():
    """Create database connection."""
    folder = os.path.dirname(DB_PATH)

    if folder:
        os.makedirs(folder, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def init_db():
    """Initialize all database tables."""

    with get_connection() as db:

        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                language TEXT DEFAULT 'bn',
                join_date TEXT,
                last_active TEXT,
                is_banned INTEGER DEFAULT 0,
                referral_count INTEGER DEFAULT 0,
                referred_by INTEGER,
                premium_package TEXT,
                premium_expiry TEXT
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                user_id INTEGER PRIMARY KEY,
                referral_balance REAL DEFAULT 0,
                deposit_balance REAL DEFAULT 0,
                task_balance REAL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                details TEXT,
                created_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                duration_days INTEGER,
                price REAL,
                active INTEGER DEFAULT 1
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                method TEXT,
                amount REAL,
                transaction_id TEXT,
                screenshot_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                method TEXT,
                account_number TEXT,
                amount REAL,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                reward REAL DEFAULT 0,
                task_type TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS task_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                screenshot_id TEXT,
                status TEXT DEFAULT 'pending',
                submitted_at TEXT,
                reviewed_at TEXT,
                UNIQUE(task_id, user_id),
                FOREIGN KEY(task_id) REFERENCES tasks(id),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS support_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_type TEXT,
                contact_value TEXT,
                active INTEGER DEFAULT 1
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                action TEXT,
                target_user INTEGER,
                reason TEXT,
                created_at TEXT
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Insert default packages only once
        package_count = db.execute(
            "SELECT COUNT(*) FROM packages"
        ).fetchone()[0]

        if package_count == 0:
            for package in DEFAULT_PACKAGES:
                db.execute("""
                    INSERT INTO packages
                    (name, duration_days, price)
                    VALUES (?, ?, ?)
                """, (
                    package["name"],
                    package["duration_days"],
                    package["price"]
                ))


def register_user(user_id, username, full_name):
    """Register a new user or update existing profile."""

    now = datetime.utcnow().isoformat()

    with get_connection() as db:

        existing = db.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        if existing:
            db.execute("""
                UPDATE users
                SET username = ?,
                    full_name = ?,
                    last_active = ?
                WHERE user_id = ?
            """, (username, full_name, now, user_id))

            return False

        db.execute("""
            INSERT INTO users
            (user_id, username, full_name, join_date, last_active)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, full_name, now, now))

        db.execute("""
            INSERT INTO wallets (user_id)
            VALUES (?)
        """, (user_id,))

        return True


def get_user(user_id):
    """Get user information."""

    with get_connection() as db:
        return db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()


def get_wallet(user_id):
    """Get user's wallet balances."""

    with get_connection() as db:
        return db.execute(
            "SELECT * FROM wallets WHERE user_id = ?",
            (user_id,)
        ).fetchone()


def get_packages():
    """Get active premium packages."""

    with get_connection() as db:
        return db.execute("""
            SELECT * FROM packages
            WHERE active = 1
            ORDER BY id
        """).fetchall()


def add_transaction(user_id, transaction_type, amount,
                    status="pending", details=""):

    """Create transaction history entry."""

    with get_connection() as db:
        cursor = db.execute("""
            INSERT INTO transactions
            (user_id, type, amount, status, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            transaction_type,
            amount,
            status,
            details,
            datetime.utcnow().isoformat()
        ))

        return cursor.lastrowid
