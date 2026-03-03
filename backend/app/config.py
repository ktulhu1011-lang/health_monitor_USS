from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    database_url: str = 'postgresql+psycopg://health:health@postgres:5432/health_monitor'
    api_key: str = 'change-me'

    google_sheet_url: str | None = 'https://docs.google.com/spreadsheets/d/1j4GyVXq16lL9Xklwwm07wquTEeJOR2HZHt6QNNE7biM/export?format=csv&gid=1375261954'
    google_sheet_id: str | None = None
    google_sheet_gid: str = '0'


settings = Settings()
