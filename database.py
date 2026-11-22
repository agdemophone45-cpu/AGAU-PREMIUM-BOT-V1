
import os
import sqlite3
from datetime import datetime, timezone

from config import DB_PATH, DEFAULT_PACKAGES


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_connection():
    folder = os.path.dirname(DB_PATH)

    if folder:
        os.makedirs(folder, exist_ok=True)

    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")

    return connection


def init_db():
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

        # Job Admin applications
        db.execute("""
            CREATE TABLE IF NOT EXISTS job_admin_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                applicant_name TEXT,
                email TEXT,
                experience TEXT,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_at TEXT,
                created_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        # Approved Job Admins and individual permissions
        db.execute("""
            CREATE TABLE IF NOT EXISTS job_admins (
                user_id INTEGER PRIMARY KEY,
                permissions TEXT DEFAULT '{}',
                active INTEGER DEFAULT 1,
                approved_by INTEGER,
                approved_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        # Private bot-mediated support tickets
        db.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_code TEXT UNIQUE,
                user_id INTEGER NOT NULL,
                ticket_type TEXT DEFAULT 'support',
                status TEXT DEFAULT 'open',
                assigned_owner INTEGER,
                created_at TEXT,
                closed_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS support_ticket_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                message TEXT,
                file_id TEXT,
                created_at TEXT,
                FOREIGN KEY(ticket_id)
                    REFERENCES support_tickets(id)
            )
        """)

        # One-time package initialization/migration.
        migration = db.execute(
            "SELECT value FROM settings WHERE key = ?",
            ("packages_v2_migrated",),
        ).fetchone()

        if not migration:
            db.execute(
                "UPDATE packages SET active = 0"
            )

            for package in DEFAULT_PACKAGES:
                existing = db.execute(
                    "SELECT id FROM packages WHERE name = ?",
                    (package["name"],),
                ).fetchone()

                if existing:
                    db.execute("""
                        UPDATE packages
                        SET duration_days = ?,
                            price = ?,
                            active = ?
                        WHERE id = ?
                    """, (
                        package["duration_days"],
                        package["price"],
                        int(package.get("active", True)),
                        existing["id"],
                    ))
                else:
                    db.execute("""
                        INSERT INTO packages
                        (name, duration_days, price, active)
                        VALUES (?, ?, ?, ?)
                    """, (
                        package["name"],
                        package["duration_days"],
                        package["price"],
                        int(package.get("active", True)),
                    ))

            db.execute("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES ('packages_v2_migrated', '1')
            """)


def register_user(user_id, username, full_name):
    now = now_iso()

    with get_connection() as db:
        existing = db.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,),
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
    with get_connection() as db:
        return db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()


def get_wallet(user_id):
    with get_connection() as db:
        return db.execute(
            "SELECT * FROM wallets WHERE user_id = ?",
            (user_id,),
        ).fetchone()


def get_packages(include_inactive=False):
    with get_connection() as db:
        if include_inactive:
            rows = db.execute("""
                SELECT * FROM packages
                ORDER BY id
            """).fetchall()
        else:
            rows = db.execute("""
                SELECT * FROM packages
                WHERE active = 1
                ORDER BY id
            """).fetchall()

        return [dict(row) for row in rows]


def add_transaction(
    user_id,
    transaction_type,
    amount,
    status="pending",
    details="",
):
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
            now_iso(),
        ))

        return cursor.lastrowid


def add_admin_log(
    admin_id,
    action,
    target_user=None,
    reason="",
):
    with get_connection() as db:
        cursor = db.execute("""
            INSERT INTO admin_logs
            (admin_id, action, target_user, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            admin_id,
            action,
            target_user,
            reason,
            now_iso(),
        ))

        return cursor.lastrowid
