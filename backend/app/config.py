from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./faceattend.db"
    admin_api_key: str = ""
    template_key: str = ""  # base64-encoded 32 bytes
    models_dir: str = "./models"

    match_threshold: float = 0.42
    match_margin: float = 0.06
    continuity_threshold: float = 0.30
    straight_max_yaw: float = 0.12
    turn_min_yaw: float = 0.20
    challenge_ttl_seconds: int = 60

    debounce_seconds: int = 120
    max_image_mb: int = 5
    max_faces_per_person: int = 5
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
