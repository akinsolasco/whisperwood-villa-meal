import sqlite3

import bcrypt
import psycopg2

from config import DATABASE_MODE, LOCAL_DB_PATH, DEMO_USERS
from db_config import DB_CONFIG


class AuthService:
    def __init__(self):
        self.conn = None
        self.backend = None

    def connect(self):
        if self.conn is not None:
            if self.backend == "sqlite":
                return
            if not self.conn.closed:
                return

        if DATABASE_MODE.lower() in {"sqlite", "local", "demo"}:
            LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(LOCAL_DB_PATH))
            self.conn.row_factory = sqlite3.Row
            self.backend = "sqlite"
            self.ensure_local_users()
            return

        config = dict(DB_CONFIG)
        config.setdefault("connect_timeout", 2)
        self.conn = psycopg2.connect(**config)
        self.backend = "postgres"
        self.ensure_user_columns()

    def close(self):
        if self.conn:
            self.conn.close()
        self.conn = None
        self.backend = None

    def ensure_local_users(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'ADMIN',
                active INTEGER NOT NULL DEFAULT 1,
                password_must_change INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.ensure_user_columns(cur)
        for username, password, role in DEMO_USERS:
            cur.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cur.fetchone():
                continue
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            cur.execute("""
                INSERT INTO users (username, password_hash, role, active)
                VALUES (?, ?, ?, 1)
            """, (username, password_hash, role))
        self.conn.commit()
        cur.close()

    def ensure_user_columns(self, cur=None):
        own_cursor = cur is None
        cur = cur or self.conn.cursor()
        try:
            if self.backend == "sqlite":
                columns = {row["name"] for row in cur.execute("PRAGMA table_info(users)").fetchall()}
                if "password_must_change" not in columns:
                    cur.execute("ALTER TABLE users ADD COLUMN password_must_change INTEGER NOT NULL DEFAULT 0")
            else:
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_must_change BOOLEAN NOT NULL DEFAULT FALSE")
            self.conn.commit()
        finally:
            if own_cursor:
                cur.close()

    def list_users(self):
        self.connect()
        cur = self.conn.cursor()
        if self.backend == "sqlite":
            cur.execute("""
                SELECT id, username, role, active, password_must_change, created_at
                FROM users
                ORDER BY username ASC
            """)
            rows = [dict(row) for row in cur.fetchall()]
        else:
            cur.execute("""
                SELECT id, username, role, active, password_must_change, created_at
                FROM users
                ORDER BY username ASC
            """)
            rows = [
                {
                    "id": row[0],
                    "username": row[1],
                    "role": row[2],
                    "active": row[3],
                    "password_must_change": row[4],
                    "created_at": row[5],
                }
                for row in cur.fetchall()
            ]
        cur.close()
        return rows

    def create_user(self, username: str, password: str, role: str, must_change_password: bool = True):
        self.connect()
        username = username.strip()
        role = role.strip().upper()
        if not username or not password:
            raise ValueError("Username and password are required.")

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cur = self.conn.cursor()
        try:
            if self.backend == "sqlite":
                cur.execute("""
                    INSERT INTO users (username, password_hash, role, active, password_must_change)
                    VALUES (?, ?, ?, 1, ?)
                """, (username, password_hash, role, int(bool(must_change_password))))
            else:
                cur.execute("""
                    INSERT INTO users (username, password_hash, role, active, password_must_change)
                    VALUES (%s, %s, %s, TRUE, %s)
                """, (username, password_hash, role, bool(must_change_password)))
            self.conn.commit()
        finally:
            cur.close()

    def change_password(self, user_id: int, current_password: str, new_password: str):
        self.connect()
        if not current_password or not new_password:
            raise ValueError("Current and new password are required.")
        if len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters.")

        cur = self.conn.cursor()
        marker = "%s" if self.backend == "postgres" else "?"
        try:
            cur.execute(f"SELECT password_hash FROM users WHERE id = {marker} AND active = {marker}", (user_id, True if self.backend == "postgres" else 1))
            row = cur.fetchone()
            if not row:
                raise ValueError("Active user account was not found.")
            password_hash = row[0] if self.backend == "postgres" else row["password_hash"]
            if not bcrypt.checkpw(current_password.encode(), password_hash.encode()):
                raise ValueError("Current password is incorrect.")

            new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            timestamp = "NOW()" if self.backend == "postgres" else "CURRENT_TIMESTAMP"
            cur.execute(f"""
                UPDATE users
                SET password_hash = {marker},
                    password_must_change = {marker},
                    updated_at = {timestamp}
                WHERE id = {marker}
            """, (new_hash, False if self.backend == "postgres" else 0, user_id))
            self.conn.commit()
        finally:
            cur.close()

    def set_temporary_password(self, user_id: int, temporary_password: str):
        self.connect()
        if not temporary_password or len(temporary_password) < 8:
            raise ValueError("Temporary password must be at least 8 characters.")

        cur = self.conn.cursor()
        marker = "%s" if self.backend == "postgres" else "?"
        try:
            cur.execute(f"SELECT id, active FROM users WHERE id = {marker}", (user_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("User account was not found.")
            active = row[1] if self.backend == "postgres" else row["active"]
            if not active:
                raise ValueError("User account is inactive. Reactivate or verify the account before issuing a temporary password.")

            password_hash = bcrypt.hashpw(temporary_password.encode(), bcrypt.gensalt()).decode()
            timestamp = "NOW()" if self.backend == "postgres" else "CURRENT_TIMESTAMP"
            cur.execute(f"""
                UPDATE users
                SET password_hash = {marker},
                    password_must_change = {marker},
                    updated_at = {timestamp}
                WHERE id = {marker}
            """, (password_hash, True if self.backend == "postgres" else 1, user_id))
            self.conn.commit()
        finally:
            cur.close()

    def login(self, username: str, password: str) -> dict:
        try:
            self.connect()
            cur = self.conn.cursor()

            marker = "%s" if self.backend == "postgres" else "?"
            cur.execute(f"""
                SELECT id, username, password_hash, role, active, password_must_change
                FROM users
                WHERE username = {marker}
            """, (username,))

            row = cur.fetchone()
            cur.close()

            if not row:
                return {"success": False, "message": "Invalid username or password", "user": None}

            if self.backend == "sqlite":
                user_id = row["id"]
                db_username = row["username"]
                password_hash = row["password_hash"]
                role = row["role"]
                active = row["active"]
                password_must_change = row["password_must_change"]
            else:
                user_id, db_username, password_hash, role, active, password_must_change = row

            if not active:
                return {"success": False, "message": "Account disabled", "user": None}

            if not bcrypt.checkpw(password.encode(), password_hash.encode()):
                return {"success": False, "message": "Invalid username or password", "user": None}

            return {
                "success": True,
                "message": "Login successful",
                "user": {
                    "id": user_id,
                    "username": db_username,
                    "role": role,
                    "password_must_change": bool(password_must_change),
                }
            }

        except psycopg2.OperationalError:
            return {
                "success": False,
                "message": "Cannot connect to network database. Connect to the network and try again.",
                "user": None,
            }
        except Exception as e:
            return {"success": False, "message": str(e), "user": None}
