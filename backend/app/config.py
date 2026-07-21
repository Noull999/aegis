from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str = "sqlite+aiosqlite:///./aegis.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-key"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
