from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_KEY: str
    JWT_ALGORITHM: str
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM_NAME: str
    GROQ_API_KEY: str
    ADMIN_EMAILS: List[str]
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
