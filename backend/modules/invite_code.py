import secrets
import string
from pathlib import Path
from typing import Optional, List, Dict
import json
from datetime import datetime

INVITE_CODES_FILE = Path(__file__).parent.parent.parent / "data" / "invite_codes.json"


def get_codes_db() -> Dict:
    INVITE_CODES_FILE.parent.mkdir(exist_ok=True)
    if not INVITE_CODES_FILE.exists():
        with open(INVITE_CODES_FILE, "w", encoding="utf-8") as f:
            json.dump({"codes": [], "used": []}, f)

    with open(INVITE_CODES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_codes_db(data: Dict):
    with open(INVITE_CODES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_invite_code(length: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


class InviteCodeManager:
    @staticmethod
    def create_code(role: str = "teacher", created_by: str = "system") -> str:
        db = get_codes_db()
        code = generate_invite_code()

        db["codes"].append(
            {
                "code": code,
                "role": role,
                "created_by": created_by,
                "created_at": datetime.now().isoformat(),
                "used": False,
            }
        )

        save_codes_db(db)
        return code

    @staticmethod
    def verify_code(code: str) -> Optional[Dict]:
        db = get_codes_db()
        for item in db["codes"]:
            if item["code"] == code and not item["used"]:
                return item
        return None

    @staticmethod
    def use_code(code: str, username: str) -> bool:
        db = get_codes_db()
        for item in db["codes"]:
            if item["code"] == code:
                item["used"] = True
                item["used_by"] = username
                item["used_at"] = datetime.now().isoformat()
                save_codes_db(db)
                return True
        return False

    @staticmethod
    def list_codes(role: str = None) -> List[Dict]:
        db = get_codes_db()
        codes = db["codes"]
        if role:
            codes = [c for c in codes if c["role"] == role]
        return codes

    @staticmethod
    def delete_code(code: str) -> bool:
        db = get_codes_db()
        original_len = len(db["codes"])
        db["codes"] = [c for c in db["codes"] if c["code"] != code]
        if len(db["codes"]) < original_len:
            save_codes_db(db)
            return True
        return False

    @staticmethod
    def get_available_codes(role: str = None) -> List[str]:
        db = get_codes_db()
        codes = [c for c in db["codes"] if not c["used"]]
        if role:
            codes = [c for c in codes if c["role"] == role]
        return [c["code"] for c in codes]


invite_code_manager = InviteCodeManager()
