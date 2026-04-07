import sqlite3
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import uuid
import jwt
from passlib.context import CryptContext
from ..core.config import get_settings
from ..core.database import init_db

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db_connection():
    init_db()
    conn = sqlite3.connect(settings.sqlite_db_path)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.deepseek_api_key or "secret_key", algorithm="HS256"
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(
            token, settings.deepseek_api_key or "secret_key", algorithms=["HS256"]
        )
        return payload
    except jwt.PyJWTError:
        return None


class AuthService:
    @staticmethod
    def register_user(
        username: str,
        password: str,
        role: str,
        email: str = None,
        real_name: str = None,
    ) -> Dict:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return {"success": False, "error": "用户名已存在"}

        user_id = str(uuid.uuid4())
        password_hash = hash_password(password)

        cursor.execute(
            """
            INSERT INTO users (id, username, password_hash, email, real_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                password_hash,
                email,
                real_name or username,
                role,
                datetime.now().isoformat(),
            ),
        )

        conn.commit()
        conn.close()

        return {"success": True, "user_id": user_id, "username": username}

    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        user = dict(row)
        if verify_password(password, user["password_hash"]):
            return user
        return None

    @staticmethod
    def login_user(username: str, password: str) -> Optional[Dict]:
        user = AuthService.authenticate_user(username, password)

        if not user:
            return None

        access_token = create_access_token(
            {"sub": user["id"], "username": user["username"], "role": user["role"]}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user.get("email"),
                "role": user["role"],
                "real_name": user.get("real_name"),
                "created_at": user.get("created_at"),
            },
        }

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    @staticmethod
    def get_all_students() -> List[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE role = ?", ("student",))
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    @staticmethod
    def get_teacher_students(teacher_id: str) -> List[Dict]:
        return AuthService.get_all_students()

    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None


auth_service = AuthService()
