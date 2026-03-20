from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "Finance Analytics API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@db:5432/finance_analytics",
        validation_alias="database_url",
    )

    # Google Sheets
    GOOGLE_SHEETS_SPREADSHEET_ID: str = ""
    GOOGLE_SHEETS_SPREADSHEET_URL: str = ""
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = "credentials/google_service_account.json"

    @property
    def spreadsheet_id(self) -> str:
        """
        Retorna o ID da planilha.
        - Prioriza `GOOGLE_SHEETS_SPREADSHEET_ID`
        - Caso vazio, extrai de `GOOGLE_SHEETS_SPREADSHEET_URL`
        """
        if self.GOOGLE_SHEETS_SPREADSHEET_ID:
            return self.GOOGLE_SHEETS_SPREADSHEET_ID.strip()

        url = (self.GOOGLE_SHEETS_SPREADSHEET_URL or "").strip()
        if "/d/" in url:
            parts = url.split("/d/")[1]
            return parts.split("/")[0]
        return url


@lru_cache()
def get_settings() -> Settings:
    return Settings()
