import secrets
import string
from typing import Optional, List, Dict
from datetime import datetime
from ..core.config import get_settings
from ..core.database import init_db

settings = get_settings()


def get_db_connection():
    init_db()
    import sqlite3

    conn = sqlite3.connect(settings.sqlite_db_path)
    conn.row_factory = sqlite3.Row
    return conn


def generate_invite_code(length: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


class InviteCodeManager:
    @staticmethod
    def create_code(role: str = "teacher", created_by: str = "system") -> str:
        conn = get_db_connection()
        cursor = conn.cursor()

        code = generate_invite_code()

        cursor.execute(
            """
            INSERT INTO invite_codes (code, role, created_by, created_at, used)
            VALUES (?, ?, ?, ?, 0)
            """,
            (code, role, created_by, datetime.now().isoformat()),
        )

        conn.commit()
        conn.close()
        return code

    @staticmethod
    def verify_code(code: str) -> Optional[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM invite_codes WHERE code = ? AND used = 0", (code,)
        )
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    @staticmethod
    def use_code(code: str, username: str) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE invite_codes
            SET used = 1, used_by = ?, used_at = ?
            WHERE code = ?
            """,
            (username, datetime.now().isoformat(), code),
        )

        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success

    @staticmethod
    def list_codes(role: str = None) -> List[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()

        if role:
            cursor.execute("SELECT * FROM invite_codes WHERE role = ?", (role,))
        else:
            cursor.execute("SELECT * FROM invite_codes")

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    @staticmethod
    def delete_code(code: str) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM invite_codes WHERE code = ?", (code,))

        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success

    @staticmethod
    def get_available_codes(role: str = None) -> List[str]:
        conn = get_db_connection()
        cursor = conn.cursor()

        if role:
            cursor.execute(
                "SELECT code FROM invite_codes WHERE used = 0 AND role = ?", (role,)
            )
        else:
            cursor.execute("SELECT code FROM invite_codes WHERE used = 0")

        rows = cursor.fetchall()
        conn.close()

        return [row["code"] for row in rows]


invite_code_manager = InviteCodeManager()
