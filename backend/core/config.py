import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    # SQLite 数据库配置
    sqlite_db_path: str = str(BASE_DIR / "data" / "users.db")

    # 向量检索配置
    embedding_model: str = "shibing624/text2vec-base-chinese"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 32
    vector_index_path: str = str(BASE_DIR / "data" / "faiss_index")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings():
    return Settings()
