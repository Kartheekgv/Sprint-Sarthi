from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Sprint Sarthi API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite+aiosqlite:///./data/sprint_sarthi.db"
    frontend_origin: str = "http://localhost:3000"
    max_upload_mb: int = Field(default=25, ge=1, le=100)
    upload_dir: Path = Path("uploads")
    export_dir: Path = Path("exports")
    llm_provider: str = "llmaas"
    llm_api_key: SecretStr | None = Field(default=None, repr=False)
    llm_base_url: str = "https://llmapi.ai.vwgroup.com"
    llm_model: str = "gpt-4o"
    llm_embedding_model: str = "text-embedding-3-large"
    llm_timeout_seconds: float = Field(default=180, gt=0, le=300)
    llmaas_client_id: str | None = None
    llmaas_client_secret: SecretStr | None = Field(default=None, repr=False)
    llmaas_token_url: str = "https://idp.cloud.vwgroup.com/auth/realms/kums-mfa/protocol/openid-connect/token"
    checkpoint_database_path: Path = Path("data/langgraph_checkpoints.sqlite")
    max_llm_context_chars: int = Field(default=24000, ge=1000, le=100000)
    embedding_provider: str = "local"

    def ensure_directories(self) -> None:
        for directory in (Path("data"), self.upload_dir, self.export_dir):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
