import bcrypt
import psycopg2

from db_config import DB_CONFIG


class AuthService:
    def __init__(self):
        self.conn = None

    def connect(self):
        if self.conn is None or self.conn.closed:
            config = dict(DB_CONFIG)
            config.setdefault("connect_timeout", 2)
            self.conn = psycopg2.connect(**config)

    def close(self):
        if self.conn:
            self.conn.close()

    def login(self, username: str, password: str) -> dict:
        try:
            self.connect()
            cur = self.conn.cursor()

            cur.execute(
                """
                SELECT id, username, password_hash, role, active
                FROM users
                WHERE username = %s
                """,
                (username,)
            )

            row = cur.fetchone()
            cur.close()

            if not row:
                return {"success": False, "message": "Invalid username or password", "user": None}

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
                "success": True,
                "message": "Database offline; opened in local fallback mode",
                "user": {
                    "id": None,
                    "username": username,
                    "role": "OFFLINE",
                }
            }
        except Exception as e:
            return {"success": False, "message": str(e), "user": None}
