import os
import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import hashlib
import uuid
import jwt
from passlib.context import CryptContext
from ..core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

USERS_FILE = Path(__file__).parent.parent.parent / "data" / "users.json"


def get_users_db() -> Dict:
    USERS_FILE.parent.mkdir(exist_ok=True)
    if not USERS_FILE.exists():
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": [], "students": []}, f)

    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users_db(data: Dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


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
        db = get_users_db()

        if any(u["username"] == username for u in db["users"]):
            return {"success": False, "error": "用户名已存在"}

        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "username": username,
            "password": hash_password(password),
            "email": email,
            "role": role,
            "real_name": real_name or username,
            "created_at": datetime.now().isoformat(),
        }

        db["users"].append(user)

        if role == "student":
            db["students"].append(
                {
                    "user_id": user_id,
                    "username": username,
                    "real_name": real_name or username,
                }
            )

        save_users_db(db)

        return {"success": True, "user_id": user_id, "username": username}

    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[Dict]:
        db = get_users_db()

        for user in db["users"]:
            if user["username"] == username:
                if verify_password(password, user["password"]):
                    return user
                return None

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
                "created_at": user["created_at"],
            },
        }

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict]:
        db = get_users_db()
        for user in db["users"]:
            if user["id"] == user_id:
                return user
        return None

    @staticmethod
    def get_all_students() -> List[Dict]:
        db = get_users_db()
        return [u for u in db["users"] if u["role"] == "student"]

    @staticmethod
    def get_teacher_students(teacher_id: str) -> List[Dict]:
        db = get_users_db()
        return [u for u in db["users"] if u["role"] == "student"]

    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict]:
        db = get_users_db()
        for user in db["users"]:
            if user["username"] == username:
                return user
        return None


auth_service = AuthService()
