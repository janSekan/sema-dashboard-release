import sqlite3
from datetime import datetime

DB_PATH = "data.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP,
            ot REAL,
            it REAL,
            wt REAL,
            ht REAL,
            pr REAL
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_measurements_ts
        ON measurements(ts)
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            role TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    seed_default_accounts(cur)
    conn.commit()
    conn.close()

def seed_default_accounts(cur):
    cur.execute("SELECT COUNT(*) FROM accounts")
    count = cur.fetchone()[0]

    if count > 0:
        return

    default_password_hash = "$argon2id$v=19$m=65536,t=3,p=4$ElxEdeMxAbYXg5S/mi2JKA$c10zAC9hDKreynKl+jXi5Rn5bI5v6zDXSOlPWEyX9Nk"

    accounts = [
        ("user", "user", default_password_hash),
        ("admin", "admin", default_password_hash),
        ("superadmin", "superadmin", default_password_hash),
    ]

    cur.executemany("""
        INSERT INTO accounts (role, username, password_hash)
        VALUES (?, ?, ?)
    """, accounts)

def get_config(key, default=None):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT value
        FROM app_settings
        WHERE key = ?
    """, (key,))

    row = cur.fetchone()
    conn.close()

    if row is None:
        return default

    return row[0]


def set_config(key, value):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP
    """, (key, str(value)))

    conn.commit()
    conn.close()


def get_account(role):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT role, username, password_hash
        FROM accounts
        WHERE role = ?
    """, (role,))

    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "role": row[0],
        "username": row[1],
        "password_hash": row[2],
    }


def set_account(role, username, password_hash):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO accounts (role, username, password_hash, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(role) DO UPDATE SET
            username = excluded.username,
            password_hash = excluded.password_hash,
            updated_at = CURRENT_TIMESTAMP
    """, (role, username, password_hash))

    conn.commit()
    conn.close()


def log_temps(outTemp, inTemp, waterTemp, heatTemp, progress):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO measurements (ot, it, wt, ht, pr)
        VALUES (?, ?, ?, ?, ?)
    """, (outTemp, inTemp, waterTemp, heatTemp, progress))

    conn.commit()
    conn.close()


def get_last_measurements(limit=200):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT ts, ot, it, wt, ht, pr
        FROM (
            SELECT ts, ot, it, wt, ht, pr
            FROM measurements
            ORDER BY ts DESC
            LIMIT ?
        )
        ORDER BY ts ASC
    """, (limit,))

    rows = cur.fetchall()
    conn.close()

    return rows