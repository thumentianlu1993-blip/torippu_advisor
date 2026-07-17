from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    DATABASE_URL: str = "postgresql+psycopg://travel:travel@postgres:5432/travel"
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    SILICONFLOW_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    XIAOHONGSHU_API_KEY: str = ""
    XIAOHONGSHU_API_BASE_URL: str = ""
    XIAOHONGSHU_API_ENDPOINT: str = ""
    TRIPADVISOR_API_KEY: str = ""
    SERPER_API_KEY: str = ""
    TAVILY_API_KEY: str = ""
    JINA_AI_ENABLED: bool = True
    FIRECRAWL_API_KEY: str = ""
    FIRECRAWL_BASE_URL: str = "https://api.firecrawl.dev/v1"
    TIKHUB_API_KEY: str = ""
    TIKHUB_XIAOHONGSHU_ENDPOINT: str = ""
    STAYAPI_API_KEY: str = ""
    DATAFORSEO_LOGIN: str = ""
    DATAFORSEO_PASSWORD: str = ""
    DIANPING_API_KEY: str = ""
    DIANPING_API_BASE_URL: str = ""
    CTRIP_API_KEY: str = ""
    CTRIP_API_BASE_URL: str = ""
    BOOKING_AFFILIATE_ID: str = ""
    AGODA_API_KEY: str = ""
    FOURSQUARE_API_KEY: str = ""
    APIFY_API_TOKEN: str = ""
    BING_SEARCH_API_KEY: str = ""
    YELP_API_KEY: str = ""
    LOG_LEVEL: str = "INFO"
    # Comma-separated list of origins allowed to call the API cross-origin.
    CORS_ORIGINS: str = "http://localhost:3000"


settings = Settings()
