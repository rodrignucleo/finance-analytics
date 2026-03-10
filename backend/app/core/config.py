from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Finance Analytics API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/finance_analytics"

    # Google Sheets
    GOOGLE_SHEETS_SPREADSHEET_URL: str = ""
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = "credentials/google_service_account.json"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def spreadsheet_id(self) -> str:
        """Extrai o ID da planilha da URL."""
        url = self.GOOGLE_SHEETS_SPREADSHEET_URL
        if "/d/" in url:
            parts = url.split("/d/")[1]
            return parts.split("/")[0]
        return url


@lru_cache()
def get_settings() -> Settings:
    return Settings()
