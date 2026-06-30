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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
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

    def list_users(self):
        self.connect()
        cur = self.conn.cursor()
        if self.backend == "sqlite":
            cur.execute("""
                SELECT id, username, role, active, created_at
                FROM users
                ORDER BY username ASC
            """)
            rows = [dict(row) for row in cur.fetchall()]
        else:
            cur.execute("""
                SELECT id, username, role, active, created_at
                FROM users
                ORDER BY username ASC
            """)
            rows = [
                {
                    "id": row[0],
                    "username": row[1],
                    "role": row[2],
                    "active": row[3],
                    "created_at": row[4],
                }
                for row in cur.fetchall()
            ]
        cur.close()
        return rows

    def create_user(self, username: str, password: str, role: str):
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
                    INSERT INTO users (username, password_hash, role, active)
                    VALUES (?, ?, ?, 1)
                """, (username, password_hash, role))
            else:
                cur.execute("""
                    INSERT INTO users (username, password_hash, role, active)
                    VALUES (%s, %s, %s, TRUE)
                """, (username, password_hash, role))
            self.conn.commit()
        finally:
            cur.close()

    def login(self, username: str, password: str) -> dict:
        try:
            self.connect()
            cur = self.conn.cursor()

            marker = "%s" if self.backend == "postgres" else "?"
            cur.execute(f"""
                SELECT id, username, password_hash, role, active
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
            else:
                user_id, db_username, password_hash, role, active = row

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
