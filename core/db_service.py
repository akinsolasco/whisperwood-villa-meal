import uuid

import psycopg2
from psycopg2.extras import RealDictCursor, Json

from db_config import DB_CONFIG


def generate_resident_uid() -> str:
    return f"RES-{uuid.uuid4().hex[:8].upper()}"


class DatabaseService:
    def __init__(self):
        self.conn = None

    def connect(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)

    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()

    def ensure_tables(self):
        self.connect()
        cur = self.conn.cursor()

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
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS device_registry (
            id SERIAL PRIMARY KEY,
            device_id VARCHAR(128) UNIQUE NOT NULL,
            ip VARCHAR(64),
            port INTEGER,
            fw VARCHAR(64),
            last_seen_s INTEGER DEFAULT 9999,
            is_online BOOLEAN DEFAULT FALSE,
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

        self.conn.commit()
        cur.close()

    def create_resident(self, data):
        self.connect()
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO residents (
                resident_uid, full_name, room, diet, allergies, note, drinks, active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data["resident_uid"],
            data["full_name"],
            data.get("room"),
            data.get("diet"),
            data.get("allergies"),
            data.get("note"),
            data.get("drinks"),
            data.get("active", True),
        ))
        resident_id = cur.fetchone()[0]
        self.conn.commit()
        cur.close()
        return resident_id

    def update_resident(self, resident_id, data):
        self.connect()
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE residents
            SET full_name=%s,
                room=%s,
                diet=%s,
                allergies=%s,
                note=%s,
                drinks=%s,
                active=%s,
                updated_at=NOW()
            WHERE id=%s
        """, (
            data["full_name"],
            data.get("room"),
            data.get("diet"),
            data.get("allergies"),
            data.get("note"),
            data.get("drinks"),
            data.get("active", True),
            resident_id,
        ))
        self.conn.commit()
        cur.close()

    def get_residents(self):
        self.connect()
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT r.*,
                   d.device_id AS paired_device_id,
                   d.is_online AS paired_device_online
            FROM residents r
            LEFT JOIN device_registry d ON d.paired_resident_id = r.id
            ORDER BY r.full_name ASC
        """)
        rows = cur.fetchall()
        cur.close()
        return rows

    def get_resident(self, resident_id):
        self.connect()
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT r.*,
                   d.device_id AS paired_device_id,
                   d.is_online AS paired_device_online
            FROM residents r
            LEFT JOIN device_registry d ON d.paired_resident_id = r.id
            WHERE r.id = %s
        """, (resident_id,))
        row = cur.fetchone()
        cur.close()
        return row

    def upsert_devices(self, devices):
        self.connect()
        cur = self.conn.cursor()
        for d in devices:
            cur.execute("""
                INSERT INTO device_registry (
                    device_id, ip, port, fw, last_seen_s, is_online, last_sync_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (device_id)
                DO UPDATE SET
                    ip = EXCLUDED.ip,
                    port = EXCLUDED.port,
                    fw = EXCLUDED.fw,
                    last_seen_s = EXCLUDED.last_seen_s,
                    is_online = EXCLUDED.is_online,
                    last_sync_at = NOW(),
                    updated_at = NOW()
            """, (
                d.id, d.ip, d.port, d.fw, d.last_seen_s, d.is_online,
            ))
        self.conn.commit()
        cur.close()

    def get_devices(self):
        self.connect()
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT d.*,
                   r.full_name AS resident_name,
                   r.resident_uid
            FROM device_registry d
            LEFT JOIN residents r ON r.id = d.paired_resident_id
            ORDER BY d.device_id ASC
        """)
        rows = cur.fetchall()
        cur.close()
        return rows

    def pair_resident_to_device(self, resident_id, device_id):
        self.connect()
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE device_registry
            SET paired_resident_id = NULL, updated_at = NOW()
            WHERE paired_resident_id = %s
        """, (resident_id,))
        cur.execute("""
            UPDATE device_registry
            SET paired_resident_id = %s, updated_at = NOW()
            WHERE device_id = %s
        """, (resident_id, device_id))
        self.conn.commit()
        cur.close()

    def unpair_device(self, device_id):
        self.connect()
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE device_registry
            SET paired_resident_id = NULL, updated_at = NOW()
            WHERE device_id = %s
        """, (device_id,))
        self.conn.commit()
        cur.close()

    def log_update(self, action_type, resident_id, resident_uid, device_id,
                   pushed_by_user_id, pushed_by_username, payload, response, success, message):
        self.connect()
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO display_updates (
                action_type, resident_id, resident_uid, device_id,
                pushed_by_user_id, pushed_by_username,
                payload_json, response_json, success, message
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            action_type,
            resident_id,
            resident_uid,
            device_id,
            pushed_by_user_id,
            pushed_by_username,
            Json(payload) if payload is not None else None,
            Json(response) if response is not None else None,
            success,
            message,
        ))
        self.conn.commit()
        cur.close()

    def get_recent_logs(self, limit=50):
        self.connect()
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT created_at, action_type, resident_uid, device_id,
                   pushed_by_username, success, message
            FROM display_updates
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        cur.close()
        return rows
