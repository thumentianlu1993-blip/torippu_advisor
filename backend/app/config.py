from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://travel:travel@postgres:5432/travel"
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    SILICONFLOW_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    XIAOHONGSHU_API_KEY: str = ""
    TRIPADVISOR_API_KEY: str = ""
    BOOKING_AFFILIATE_ID: str = ""
    AGODA_API_KEY: str = ""
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
