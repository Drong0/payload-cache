from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CACHE_SERVICE_", env_file=".env")

    database_url: str
    transformer_delay_seconds: float = Field(default=0.5, ge=0)
