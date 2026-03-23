from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./venomai.db"
    anthropic_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]
    scanner_timeout: int = 10
    scanner_user_agent: str = "VenomAI/0.1 Security Scanner (authorized)"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
