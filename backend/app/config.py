from pathlib import Path

from pydantic_settings import BaseSettings


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_URL = f"sqlite+aiosqlite:///{(BACKEND_DIR / 'venomai.db').as_posix()}"
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    database_url: str = DEFAULT_DB_URL
    anthropic_api_key: str = ""
    github_token: str = ""
    local_repos_dir: str = ""
    cors_origins: list[str] = ["http://localhost:4500", "http://127.0.0.1:4500"]
    scanner_timeout: int = 10
    scanner_user_agent: str = "VenomAI/0.1 Security Scanner (authorized)"

    model_config = {"env_file": str(ENV_FILE), "env_file_encoding": "utf-8"}


settings = Settings()
