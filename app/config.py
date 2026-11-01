import json
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    admin_ids: str = ""
    database_url: str
    ai_base_url: str = "https://api.openai.com/v1"
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_temperature: float = 0.4
    business_config_path: str = "business.json"
    timezone: str = "Asia/Tashkent"
    daily_report_time: str = "21:00"  # HH:MM in Asia/Tashkent
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def admins(self) -> set[int]:
        return {int(x.strip()) for x in self.admin_ids.split(",") if x.strip().isdigit()}

    def load_business(self) -> dict:
        return json.loads(Path(self.business_config_path).read_text(encoding="utf-8"))


settings = Settings()
