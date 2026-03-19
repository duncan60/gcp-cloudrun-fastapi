import os


class Settings:
    ENV: str = os.environ.get("ENV", "development")
    APP_TITLE: str = f"My FastAPI Service ({ENV})"
    DEBUG: bool = ENV != "production"


settings = Settings()
