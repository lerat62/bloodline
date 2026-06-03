import sqlite3
import secrets
import string
from datetime import datetime, timedelta

DB_PATH = r"C:\Users\ponpo\OneDrive\Bureau\bot rp test\rp_bot.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(col["name"] == column_name for col in columns)


def init_premium_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS premium_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_key TEXT NOT NULL UNIQUE,
        plan_name TEXT NOT NULL,
        duration_days INTEGER NOT NULL,
        max_uses INTEGER NOT NULL DEFAULT 1,
        used_count INTEGER NOT NULL DEFAULT 0,
        created_by TEXT DEFAULT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        expires_at TEXT DEFAULT NULL,
        is_disabled INTEGER NOT NULL DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guild_premium (
        guild_id INTEGER PRIMARY KEY,
        plan_name TEXT NOT NULL,
        activated_by_user_id INTEGER NOT NULL,
        license_key TEXT NOT NULL,
        activated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        expires_at TEXT DEFAULT NULL,
        is_active INTEGER NOT NULL DEFAULT 1
    )
    """)

    # Corrige les anciennes tables si des colonnes manquent
    if not column_exists(cursor, "premium_keys", "license_key"):
        raise RuntimeError("La table premium_keys existe mais ne correspond pas au bon format. Sauvegarde la DB puis recrée la table.")

    if not column_exists(cursor, "premium_keys", "plan_name"):
        cursor.execute("ALTER TABLE premium_keys ADD COLUMN plan_name TEXT NOT NULL DEFAULT 'Premium'")
    if not column_exists(cursor, "premium_keys", "duration_days"):
        cursor.execute("ALTER TABLE premium_keys ADD COLUMN duration_days INTEGER NOT NULL DEFAULT 30")
    if not column_exists(cursor, "premium_keys", "max_uses"):
        cursor.execute("ALTER TABLE premium_keys ADD COLUMN max_uses INTEGER NOT NULL DEFAULT 1")
    if not column_exists(cursor, "premium_keys", "used_count"):
        cursor.execute("ALTER TABLE premium_keys ADD COLUMN used_count INTEGER NOT NULL DEFAULT 0")
    if not column_exists(cursor, "premium_keys", "created_by"):
        cursor.execute("ALTER TABLE premium_keys ADD COLUMN created_by TEXT DEFAULT NULL")
    if not column_exists(cursor, "premium_keys", "created_at"):
        cursor.execute("ALTER TABLE premium_keys ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
    if not column_exists(cursor, "premium_keys", "expires_at"):
        cursor.execute("ALTER TABLE premium_keys ADD COLUMN expires_at TEXT DEFAULT NULL")
    if not column_exists(cursor, "premium_keys", "is_disabled"):
        cursor.execute("ALTER TABLE premium_keys ADD COLUMN is_disabled INTEGER NOT NULL DEFAULT 0")

    if not column_exists(cursor, "guild_premium", "plan_name"):
        cursor.execute("ALTER TABLE guild_premium ADD COLUMN plan_name TEXT NOT NULL DEFAULT 'Premium'")
    if not column_exists(cursor, "guild_premium", "activated_by_user_id"):
        cursor.execute("ALTER TABLE guild_premium ADD COLUMN activated_by_user_id INTEGER NOT NULL DEFAULT 0")
    if not column_exists(cursor, "guild_premium", "license_key"):
        cursor.execute("ALTER TABLE guild_premium ADD COLUMN license_key TEXT NOT NULL DEFAULT ''")
    if not column_exists(cursor, "guild_premium", "activated_at"):
        cursor.execute("ALTER TABLE guild_premium ADD COLUMN activated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    if not column_exists(cursor, "guild_premium", "expires_at"):
        cursor.execute("ALTER TABLE guild_premium ADD COLUMN expires_at TEXT DEFAULT NULL")
    if not column_exists(cursor, "guild_premium", "is_active"):
        cursor.execute("ALTER TABLE guild_premium ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")

    conn.commit()
    conn.close()


def generate_premium_key(prefix="BL"):
    alphabet = string.ascii_uppercase + string.digits
    parts = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4)]
    return f"{prefix}-" + "-".join(parts)


def create_premium_key(
    plan_name: str,
    duration_days: int,
    max_uses: int = 1,
    created_by: str | None = None,
    key_expiration_days: int | None = None
):
    init_premium_tables()

    conn = get_connection()
    cursor = conn.cursor()

    license_key = generate_premium_key()
    key_expires_at = None

    if key_expiration_days is not None and key_expiration_days > 0:
        key_expires_at = (datetime.utcnow() + timedelta(days=key_expiration_days)).isoformat(sep=" ", timespec="seconds")

    cursor.execute("""
    INSERT INTO premium_keys (
        license_key,
        plan_name,
        duration_days,
        max_uses,
        used_count,
        created_by,
        expires_at,
        is_disabled
    )
    VALUES (?, ?, ?, ?, 0, ?, ?, 0)
    """, (
        license_key,
        plan_name,
        duration_days,
        max_uses,
        created_by,
        key_expires_at
    ))

    conn.commit()
    conn.close()
    return license_key


def get_premium_key(license_key: str):
    init_premium_tables()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM premium_keys
    WHERE license_key = ?
    """, (license_key.strip(),))

    row = cursor.fetchone()
    conn.close()
    return row


def get_guild_premium(guild_id: int):
    init_premium_tables()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM guild_premium
    WHERE guild_id = ?
    """, (int(guild_id),))

    row = cursor.fetchone()
    conn.close()
    return row


def cleanup_expired_guild_premium():
    init_premium_tables()

    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")

    cursor.execute("""
    UPDATE guild_premium
    SET is_active = 0
    WHERE expires_at IS NOT NULL
      AND expires_at <= ?
    """, (now,))

    conn.commit()
    conn.close()


def cleanup_expired_keys():
    init_premium_tables()

    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")

    cursor.execute("""
    UPDATE premium_keys
    SET is_disabled = 1
    WHERE expires_at IS NOT NULL
      AND expires_at <= ?
    """, (now,))

    conn.commit()
    conn.close()


def activate_premium_key(license_key: str, guild_id: int, activated_by_user_id: int):
    init_premium_tables()
    cleanup_expired_guild_premium()
    cleanup_expired_keys()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM premium_keys
    WHERE license_key = ?
    """, (license_key.strip(),))
    key_row = cursor.fetchone()

    if not key_row:
        conn.close()
        return False, "Clé premium introuvable."

    if int(key_row["is_disabled"]) == 1:
        conn.close()
        return False, "Cette clé premium est désactivée ou expirée."

    if int(key_row["used_count"]) >= int(key_row["max_uses"]):
        conn.close()
        return False, "Cette clé premium a déjà atteint sa limite d'utilisation."

    cursor.execute("""
    SELECT *
    FROM guild_premium
    WHERE guild_id = ?
    """, (int(guild_id),))
    guild_row = cursor.fetchone()

    now = datetime.utcnow()
    duration_days = int(key_row["duration_days"])
    plan_name = key_row["plan_name"]

    if guild_row and int(guild_row["is_active"]) == 1:
        current_expires_at = guild_row["expires_at"]

        if current_expires_at:
            current_expiry_dt = datetime.fromisoformat(current_expires_at)
            start_date = current_expiry_dt if current_expiry_dt > now else now
        else:
            conn.close()
            return False, "Ce serveur a déjà un premium à vie actif."

        if duration_days <= 0:
            new_expires_at = None
        else:
            new_expires_at = (start_date + timedelta(days=duration_days)).isoformat(sep=" ", timespec="seconds")

        cursor.execute("""
        UPDATE guild_premium
        SET plan_name = ?,
            activated_by_user_id = ?,
            license_key = ?,
            activated_at = CURRENT_TIMESTAMP,
            expires_at = ?,
            is_active = 1
        WHERE guild_id = ?
        """, (
            plan_name,
            int(activated_by_user_id),
            license_key.strip(),
            new_expires_at,
            int(guild_id)
        ))
    else:
        if duration_days <= 0:
            expires_at = None
        else:
            expires_at = (now + timedelta(days=duration_days)).isoformat(sep=" ", timespec="seconds")

        cursor.execute("""
        INSERT INTO guild_premium (
            guild_id,
            plan_name,
            activated_by_user_id,
            license_key,
            activated_at,
            expires_at,
            is_active
        )
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, 1)
        ON CONFLICT(guild_id)
        DO UPDATE SET
            plan_name = excluded.plan_name,
            activated_by_user_id = excluded.activated_by_user_id,
            license_key = excluded.license_key,
            activated_at = CURRENT_TIMESTAMP,
            expires_at = excluded.expires_at,
            is_active = 1
        """, (
            int(guild_id),
            plan_name,
            int(activated_by_user_id),
            license_key.strip(),
            expires_at
        ))

    cursor.execute("""
    UPDATE premium_keys
    SET used_count = used_count + 1
    WHERE license_key = ?
    """, (license_key.strip(),))

    conn.commit()
    conn.close()

    return True, "Premium activé avec succès sur le serveur."


def disable_premium_key(license_key: str):
    init_premium_tables()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE premium_keys
    SET is_disabled = 1
    WHERE license_key = ?
    """, (license_key.strip(),))

    conn.commit()
    conn.close()
