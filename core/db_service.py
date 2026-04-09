import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor, Json

from config import APP_DATA_DIR, BASE_DIR
from db_config import DB_CONFIG


def generate_resident_uid() -> str:
    return f"RES-{uuid.uuid4().hex[:8].upper()}"


class DatabaseService:
    def __init__(self):
        self.conn = None
        self.backend = None
        self.local_path = Path(APP_DATA_DIR) / "whisperwood_local.sqlite3"

    def connect(self):
        if self.backend == "postgres" and self.conn is not None and not self.conn.closed:
            return
        if self.backend == "sqlite" and self.conn is not None:
            return

        try:
            config = dict(DB_CONFIG)
            config.setdefault("connect_timeout", 2)
            self.conn = psycopg2.connect(**config)
            self.backend = "postgres"
        except Exception:
            try:
                APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
                self.conn = sqlite3.connect(self.local_path)
                self.conn.execute("CREATE TABLE IF NOT EXISTS __connection_check (id INTEGER)")
                self.conn.execute("INSERT INTO __connection_check DEFAULT VALUES")
                self.conn.execute("DELETE FROM __connection_check")
                self.conn.commit()
            except sqlite3.OperationalError:
                if self.conn is not None:
                    self.conn.close()
                fallback_dir = Path(BASE_DIR) / "data"
                fallback_dir.mkdir(parents=True, exist_ok=True)
                self.local_path = fallback_dir / "whisperwood_local.sqlite3"
                self.conn = sqlite3.connect(self.local_path)
                self.conn.execute("CREATE TABLE IF NOT EXISTS __connection_check (id INTEGER)")
                self.conn.execute("INSERT INTO __connection_check DEFAULT VALUES")
                self.conn.execute("DELETE FROM __connection_check")
                self.conn.commit()
            self.conn.row_factory = sqlite3.Row
            self.backend = "sqlite"

    def close(self):
        if self.conn and self.backend == "postgres" and not self.conn.closed:
            self.conn.close()
        elif self.conn and self.backend == "sqlite":
            self.conn.close()
        self.conn = None
        self.backend = None

    def _cursor(self, dict_rows=False):
        self.connect()
        if self.backend == "postgres" and dict_rows:
            return self.conn.cursor(cursor_factory=RealDictCursor)
        return self.conn.cursor()

    def _rows(self, rows):
        if self.backend == "sqlite":
            return [dict(row) for row in rows]
        return rows

    def _row(self, row):
        if row is None:
            return None
        if self.backend == "sqlite":
            return dict(row)
        return row

    def _json_value(self, value):
        if value is None:
            return None
        if self.backend == "postgres":
            return Json(value)
        return json.dumps(value)

    def _add_resident_columns(self, cur):
        columns = {
            row["name"] if self.backend == "sqlite" else row[0]
            for row in cur.execute("PRAGMA table_info(residents)").fetchall()
        }
        additions = {
            "schedule": "ALTER TABLE residents ADD COLUMN schedule TEXT",
            "source_document": "ALTER TABLE residents ADD COLUMN source_document TEXT",
            "safety_review_note": "ALTER TABLE residents ADD COLUMN safety_review_note TEXT",
            "needs_safety_review": "ALTER TABLE residents ADD COLUMN needs_safety_review BOOLEAN NOT NULL DEFAULT 0",
            "lcd_image_path": "ALTER TABLE residents ADD COLUMN lcd_image_path TEXT",
            "lcd_schedule_enabled": "ALTER TABLE residents ADD COLUMN lcd_schedule_enabled BOOLEAN NOT NULL DEFAULT 0",
            "lcd_on_time": "ALTER TABLE residents ADD COLUMN lcd_on_time TEXT",
            "lcd_off_time": "ALTER TABLE residents ADD COLUMN lcd_off_time TEXT",
            "sleep_if_no_image": "ALTER TABLE residents ADD COLUMN sleep_if_no_image BOOLEAN NOT NULL DEFAULT 0",
        }
        for column, sql in additions.items():
            if column not in columns:
                cur.execute(sql)

    def ensure_tables(self):
        self.connect()
        cur = self.conn.cursor()

        if self.backend == "postgres":
            cur.execute("""
            CREATE TABLE IF NOT EXISTS residents (
                id SERIAL PRIMARY KEY,
                resident_uid VARCHAR(32) UNIQUE NOT NULL,
                full_name VARCHAR(255) NOT NULL,
                room VARCHAR(64),
                diet TEXT,
                allergies TEXT,
                note TEXT,
                drinks TEXT,
                schedule TEXT,
                source_document TEXT,
                safety_review_note TEXT,
                needs_safety_review BOOLEAN NOT NULL DEFAULT FALSE,
                lcd_image_path TEXT,
                lcd_schedule_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                lcd_on_time TEXT,
                lcd_off_time TEXT,
                sleep_if_no_image BOOLEAN NOT NULL DEFAULT FALSE,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """)
            for column_sql in [
                "ALTER TABLE residents ADD COLUMN IF NOT EXISTS schedule TEXT",
                "ALTER TABLE residents ADD COLUMN IF NOT EXISTS source_document TEXT",
                "ALTER TABLE residents ADD COLUMN IF NOT EXISTS safety_review_note TEXT",
                "ALTER TABLE residents ADD COLUMN IF NOT EXISTS needs_safety_review BOOLEAN NOT NULL DEFAULT FALSE",
                "ALTER TABLE residents ADD COLUMN IF NOT EXISTS lcd_image_path TEXT",
                "ALTER TABLE residents ADD COLUMN IF NOT EXISTS lcd_schedule_enabled BOOLEAN NOT NULL DEFAULT FALSE",
                "ALTER TABLE residents ADD COLUMN IF NOT EXISTS lcd_on_time TEXT",
                "ALTER TABLE residents ADD COLUMN IF NOT EXISTS lcd_off_time TEXT",
                "ALTER TABLE residents ADD COLUMN IF NOT EXISTS sleep_if_no_image BOOLEAN NOT NULL DEFAULT FALSE",
            ]:
                cur.execute(column_sql)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS device_registry (
                id SERIAL PRIMARY KEY,
                device_id VARCHAR(128) UNIQUE NOT NULL,
                ip VARCHAR(64),
                port INTEGER,
                fw VARCHAR(64),
                last_seen_s INTEGER DEFAULT 9999,
                is_online BOOLEAN DEFAULT FALSE,
                battery_level INTEGER,
                paired_resident_id INTEGER NULL REFERENCES residents(id) ON DELETE SET NULL,
                last_sync_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS display_updates (
                id SERIAL PRIMARY KEY,
                action_type VARCHAR(64) NOT NULL,
                resident_id INTEGER NULL REFERENCES residents(id) ON DELETE SET NULL,
                resident_uid VARCHAR(32),
                device_id VARCHAR(128),
                pushed_by_user_id INTEGER,
                pushed_by_username VARCHAR(255),
                payload_json JSONB,
                response_json JSONB,
                success BOOLEAN NOT NULL DEFAULT FALSE,
                message TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """)
            cur.execute("ALTER TABLE device_registry ADD COLUMN IF NOT EXISTS battery_level INTEGER")
        else:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS residents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resident_uid TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                room TEXT,
                diet TEXT,
                allergies TEXT,
                note TEXT,
                drinks TEXT,
                schedule TEXT,
                source_document TEXT,
                safety_review_note TEXT,
                needs_safety_review INTEGER NOT NULL DEFAULT 0,
                lcd_image_path TEXT,
                lcd_schedule_enabled INTEGER NOT NULL DEFAULT 0,
                lcd_on_time TEXT,
                lcd_off_time TEXT,
                sleep_if_no_image INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """)
            self._add_resident_columns(cur)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS device_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT UNIQUE NOT NULL,
                ip TEXT,
                port INTEGER,
                fw TEXT,
                last_seen_s INTEGER DEFAULT 9999,
                is_online INTEGER DEFAULT 0,
                battery_level INTEGER,
                paired_resident_id INTEGER NULL REFERENCES residents(id) ON DELETE SET NULL,
                last_sync_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """)
            device_columns = {row["name"] for row in cur.execute("PRAGMA table_info(device_registry)").fetchall()}
            if "battery_level" not in device_columns:
                cur.execute("ALTER TABLE device_registry ADD COLUMN battery_level INTEGER")
            cur.execute("""
            CREATE TABLE IF NOT EXISTS display_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                resident_id INTEGER NULL REFERENCES residents(id) ON DELETE SET NULL,
                resident_uid TEXT,
                device_id TEXT,
                pushed_by_user_id INTEGER,
                pushed_by_username TEXT,
                payload_json TEXT,
                response_json TEXT,
                success INTEGER NOT NULL DEFAULT 0,
                message TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """)

        self.conn.commit()
        cur.close()

    def create_resident(self, data):
        cur = self._cursor()
        values = (
            data["resident_uid"],
            data["full_name"],
            data.get("room"),
            data.get("diet"),
            data.get("allergies"),
            data.get("note"),
            data.get("drinks"),
            data.get("schedule"),
            data.get("source_document"),
            data.get("safety_review_note"),
            data.get("needs_safety_review", False),
            data.get("lcd_image_path"),
            data.get("lcd_schedule_enabled", False),
            data.get("lcd_on_time"),
            data.get("lcd_off_time"),
            data.get("sleep_if_no_image", False),
            data.get("active", True),
        )
        if self.backend == "postgres":
            cur.execute("""
                INSERT INTO residents (
                    resident_uid, full_name, room, diet, allergies, note, drinks,
                    schedule, source_document, safety_review_note, needs_safety_review,
                    lcd_image_path, lcd_schedule_enabled, lcd_on_time, lcd_off_time, sleep_if_no_image, active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, values)
            resident_id = cur.fetchone()[0]
        else:
            cur.execute("""
                INSERT INTO residents (
                    resident_uid, full_name, room, diet, allergies, note, drinks,
                    schedule, source_document, safety_review_note, needs_safety_review,
                    lcd_image_path, lcd_schedule_enabled, lcd_on_time, lcd_off_time, sleep_if_no_image, active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, values)
            resident_id = cur.lastrowid
        self.conn.commit()
        cur.close()
        return resident_id

    def update_resident(self, resident_id, data):
        cur = self._cursor()
        values = (
            data["full_name"],
            data.get("room"),
            data.get("diet"),
            data.get("allergies"),
            data.get("note"),
            data.get("drinks"),
            data.get("schedule"),
            data.get("source_document"),
            data.get("safety_review_note"),
            data.get("needs_safety_review", False),
            data.get("lcd_image_path"),
            data.get("lcd_schedule_enabled", False),
            data.get("lcd_on_time"),
            data.get("lcd_off_time"),
            data.get("sleep_if_no_image", False),
            data.get("active", True),
            resident_id,
        )
        if self.backend == "postgres":
            cur.execute("""
                UPDATE residents
                SET full_name=%s,
                    room=%s,
                    diet=%s,
                    allergies=%s,
                    note=%s,
                    drinks=%s,
                    schedule=%s,
                    source_document=%s,
                    safety_review_note=%s,
                    needs_safety_review=%s,
                    lcd_image_path=%s,
                    lcd_schedule_enabled=%s,
                    lcd_on_time=%s,
                    lcd_off_time=%s,
                    sleep_if_no_image=%s,
                    active=%s,
                    updated_at=NOW()
                WHERE id=%s
            """, values)
        else:
            cur.execute("""
                UPDATE residents
                SET full_name=?,
                    room=?,
                    diet=?,
                    allergies=?,
                    note=?,
                    drinks=?,
                    schedule=?,
                    source_document=?,
                    safety_review_note=?,
                    needs_safety_review=?,
                    lcd_image_path=?,
                    lcd_schedule_enabled=?,
                    lcd_on_time=?,
                    lcd_off_time=?,
                    sleep_if_no_image=?,
                    active=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, values)
        self.conn.commit()
        cur.close()

    def get_residents(self):
        cur = self._cursor(dict_rows=True)
        cur.execute("""
            SELECT r.*,
                   d.device_id AS paired_device_id,
                   d.is_online AS paired_device_online
            FROM residents r
            LEFT JOIN device_registry d ON d.paired_resident_id = r.id
            ORDER BY r.full_name ASC
        """)
        rows = self._rows(cur.fetchall())
        cur.close()
        return rows

    def get_resident(self, resident_id):
        cur = self._cursor(dict_rows=True)
        marker = "%s" if self.backend == "postgres" else "?"
        cur.execute(f"""
            SELECT r.*,
                   d.device_id AS paired_device_id,
                   d.is_online AS paired_device_online
            FROM residents r
            LEFT JOIN device_registry d ON d.paired_resident_id = r.id
            WHERE r.id = {marker}
        """, (resident_id,))
        row = self._row(cur.fetchone())
        cur.close()
        return row

    def upsert_devices(self, devices):
        cur = self._cursor()
        timestamp = "NOW()" if self.backend == "postgres" else "CURRENT_TIMESTAMP"
        if self.backend == "postgres":
            cur.execute(f"UPDATE device_registry SET is_online = FALSE, last_seen_s = 9999, updated_at = {timestamp}")
        else:
            cur.execute(f"UPDATE device_registry SET is_online = 0, last_seen_s = 9999, updated_at = {timestamp}")

        for d in devices:
            if self.backend == "postgres":
                cur.execute("""
                    INSERT INTO device_registry (
                        device_id, ip, port, fw, last_seen_s, is_online, battery_level, last_sync_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (device_id)
                    DO UPDATE SET
                        ip = EXCLUDED.ip,
                        port = EXCLUDED.port,
                        fw = EXCLUDED.fw,
                        last_seen_s = EXCLUDED.last_seen_s,
                        is_online = EXCLUDED.is_online,
                        battery_level = EXCLUDED.battery_level,
                        last_sync_at = NOW(),
                        updated_at = NOW()
                """, (d.id, d.ip, d.port, d.fw, d.last_seen_s, True, d.battery_level))
            else:
                cur.execute("""
                    INSERT INTO device_registry (
                        device_id, ip, port, fw, last_seen_s, is_online, battery_level, last_sync_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(device_id)
                    DO UPDATE SET
                        ip = excluded.ip,
                        port = excluded.port,
                        fw = excluded.fw,
                        last_seen_s = excluded.last_seen_s,
                        is_online = excluded.is_online,
                        battery_level = excluded.battery_level,
                        last_sync_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """, (d.id, d.ip, d.port, d.fw, d.last_seen_s, 1, d.battery_level))
        self.conn.commit()
        cur.close()

    def get_devices(self):
        cur = self._cursor(dict_rows=True)
        cur.execute("""
            SELECT d.*,
                   r.full_name AS resident_name,
                   r.resident_uid
            FROM device_registry d
            LEFT JOIN residents r ON r.id = d.paired_resident_id
            ORDER BY d.device_id ASC
        """)
        rows = self._rows(cur.fetchall())
        cur.close()
        return rows

    def pair_resident_to_device(self, resident_id, device_id):
        cur = self._cursor()
        marker = "%s" if self.backend == "postgres" else "?"
        timestamp = "NOW()" if self.backend == "postgres" else "CURRENT_TIMESTAMP"
        cur.execute(f"""
            UPDATE device_registry
            SET paired_resident_id = NULL, updated_at = {timestamp}
            WHERE paired_resident_id = {marker}
        """, (resident_id,))
        cur.execute(f"""
            UPDATE device_registry
            SET paired_resident_id = {marker}, updated_at = {timestamp}
            WHERE device_id = {marker}
        """, (resident_id, device_id))
        self.conn.commit()
        cur.close()

    def unpair_device(self, device_id):
        cur = self._cursor()
        marker = "%s" if self.backend == "postgres" else "?"
        timestamp = "NOW()" if self.backend == "postgres" else "CURRENT_TIMESTAMP"
        cur.execute(f"""
            UPDATE device_registry
            SET paired_resident_id = NULL, updated_at = {timestamp}
            WHERE device_id = {marker}
        """, (device_id,))
        self.conn.commit()
        cur.close()

    def delete_resident(self, resident_id):
        cur = self._cursor()
        marker = "%s" if self.backend == "postgres" else "?"
        timestamp = "NOW()" if self.backend == "postgres" else "CURRENT_TIMESTAMP"
        cur.execute(f"""
            UPDATE device_registry
            SET paired_resident_id = NULL, updated_at = {timestamp}
            WHERE paired_resident_id = {marker}
        """, (resident_id,))
        cur.execute(f"DELETE FROM residents WHERE id = {marker}", (resident_id,))
        self.conn.commit()
        cur.close()

    def log_update(self, action_type, resident_id, resident_uid, device_id,
                   pushed_by_user_id, pushed_by_username, payload, response, success, message):
        cur = self._cursor()
        values = (
            action_type,
            resident_id,
            resident_uid,
            device_id,
            pushed_by_user_id,
            pushed_by_username,
            self._json_value(payload),
            self._json_value(response),
            success,
            message,
        )
        marker = "%s" if self.backend == "postgres" else "?"
        cur.execute(f"""
            INSERT INTO display_updates (
                action_type, resident_id, resident_uid, device_id,
                pushed_by_user_id, pushed_by_username,
                payload_json, response_json, success, message
            )
            VALUES ({", ".join([marker] * 10)})
        """, values)
        self.conn.commit()
        cur.close()

    def get_recent_logs(self, limit=50):
        cur = self._cursor(dict_rows=True)
        marker = "%s" if self.backend == "postgres" else "?"
        order_clause = "created_at DESC, id DESC" if self.backend == "postgres" else "datetime(created_at) DESC, id DESC"
        cur.execute(f"""
            SELECT id, created_at, action_type, resident_uid, device_id,
                   pushed_by_username, success, message, payload_json, response_json
            FROM display_updates
            ORDER BY {order_clause}
            LIMIT {marker}
        """, (limit,))
        rows = self._rows(cur.fetchall())
        cur.close()
        return rows

    def get_log(self, log_id):
        cur = self._cursor(dict_rows=True)
        marker = "%s" if self.backend == "postgres" else "?"
        cur.execute(f"""
            SELECT *
            FROM display_updates
            WHERE id = {marker}
        """, (log_id,))
        row = self._row(cur.fetchone())
        cur.close()
        return row

    def save_resident_schedule(self, resident_id, enabled, on_time, off_time, sleep_if_no_image):
        cur = self._cursor()
        marker = "%s" if self.backend == "postgres" else "?"
        timestamp = "NOW()" if self.backend == "postgres" else "CURRENT_TIMESTAMP"
        cur.execute(f"""
            UPDATE residents
            SET lcd_schedule_enabled = {marker},
                lcd_on_time = {marker},
                lcd_off_time = {marker},
                sleep_if_no_image = {marker},
                updated_at = {timestamp}
            WHERE id = {marker}
        """, (enabled, on_time, off_time, sleep_if_no_image, resident_id))
        self.conn.commit()
        cur.close()

    def get_schedule_rows(self):
        cur = self._cursor(dict_rows=True)
        cur.execute("""
            SELECT r.id,
                   r.resident_uid,
                   r.full_name,
                   r.lcd_schedule_enabled,
                   r.lcd_on_time,
                   r.lcd_off_time,
                   r.sleep_if_no_image,
                   r.lcd_image_path,
                   d.device_id,
                   d.is_online
            FROM residents r
            LEFT JOIN device_registry d ON d.paired_resident_id = r.id
            ORDER BY r.full_name ASC
        """)
        rows = self._rows(cur.fetchall())
        cur.close()
        return rows

    def get_dashboard_summary(self):
        cur = self._cursor(dict_rows=True)
        active_filter = "active = TRUE" if self.backend == "postgres" else "active = 1"
        inactive_filter = "active = FALSE" if self.backend == "postgres" else "active = 0"
        online_filter = "is_online = TRUE" if self.backend == "postgres" else "is_online = 1"
        failed_filter = "success = FALSE" if self.backend == "postgres" else "success = 0"
        review_filter = "needs_safety_review = TRUE" if self.backend == "postgres" else "needs_safety_review = 1"
        today_logs_filter = "DATE(created_at) = CURRENT_DATE" if self.backend == "postgres" else "DATE(created_at, 'localtime') = DATE('now', 'localtime')"

        cur.execute(f"SELECT COUNT(*) AS count FROM residents WHERE {active_filter}")
        active = self._row(cur.fetchone())["count"]
        cur.execute(f"SELECT COUNT(*) AS count FROM residents WHERE {inactive_filter}")
        inactive = self._row(cur.fetchone())["count"]
        cur.execute(f"SELECT COUNT(*) AS count FROM device_registry WHERE {online_filter}")
        online = self._row(cur.fetchone())["count"]
        cur.execute("SELECT COUNT(*) AS count FROM device_registry")
        known_devices = self._row(cur.fetchone())["count"]
        cur.execute("SELECT COUNT(*) AS count FROM device_registry WHERE paired_resident_id IS NOT NULL")
        paired = self._row(cur.fetchone())["count"]
        cur.execute(f"SELECT COUNT(*) AS count FROM display_updates WHERE {failed_filter}")
        failed_updates = self._row(cur.fetchone())["count"]
        cur.execute(f"SELECT COUNT(*) AS count FROM display_updates WHERE {today_logs_filter}")
        recent_activity_today = self._row(cur.fetchone())["count"]
        cur.execute("SELECT COUNT(*) AS count FROM display_updates")
        recent_activity_total = self._row(cur.fetchone())["count"]
        cur.execute(f"SELECT COUNT(*) AS count FROM residents WHERE {review_filter}")
        safety_reviews = self._row(cur.fetchone())["count"]
        cur.close()
        return {
            "active_residents": active,
            "inactive_residents": inactive,
            "online_devices": online,
            "known_devices": known_devices,
            "paired_devices": paired,
            "failed_updates": failed_updates,
            "recent_activity": recent_activity_today,
            "recent_activity_today": recent_activity_today,
            "recent_activity_total": recent_activity_total,
            "safety_reviews": safety_reviews,
            "database_mode": self.backend or "unknown",
        }

    @staticmethod
    def format_timestamp(value):
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return str(value or "")
