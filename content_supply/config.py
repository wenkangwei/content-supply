"""Application configuration via Pydantic Settings."""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = PROJECT_ROOT / "configs"


class MySQLConfig(BaseSettings):
    host: str = "localhost"
    port: int = 3306
    user: str = "rec_user"
    password: str = "rec_pass"
    database: str = "rec_platform"
    pool_size: int = 5

    @property
    def dsn(self) -> str:
        return f"mysql+aiomysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class RedisConfig(BaseSettings):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None


class LLMConfig(BaseSettings):
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "ollama"
    model: str = "qwen2.5:7b"
    max_tokens: int = 2048
    temperature: float = 0.7


class SchedulerConfig(BaseSettings):
    enabled: bool = True
    rss_default_interval: int = 1800  # seconds
    hot_track_interval: int = 3600  # seconds
    cleanup_cron: str = "0 3 * * *"  # daily 3am
    rewrite_cron: str = "0 4 * * *"  # daily 4am
    tag_mining_cron: str = "0 2 * * 0"  # weekly sunday 2am


class NotificationConfig(BaseSettings):
    enabled: bool = False
    webhook_url: Optional[str] = None
    email_to: Optional[str] = None
    email_from: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    auto_confirm_after_hours: int = 24


class ServerConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8010
    workers: int = 1
    log_level: str = "info"


class AppConfig(BaseSettings):
    mysql: MySQLConfig = Field(default_factory=MySQLConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)


def load_app_config(config_path: Optional[Path] = None) -> AppConfig:
    """Load config from YAML file, falling back to defaults/env vars."""
    config = AppConfig()
    path = config_path or CONFIGS_DIR / "app.yaml"
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        # Override with YAML values
        for section_key in ("mysql", "redis", "llm", "scheduler", "notification", "server"):
            if section_key in data:
                section_data = data[section_key]
                section_obj = getattr(config, section_key)
                for k, v in section_data.items():
                    # Support ${env:VAR:default} syntax
                    if isinstance(v, str) and v.startswith("${env:") and v.endswith("}"):
                        inner = v[6:-1]
                        parts = inner.split(":", 1)
                        import os
                        v = os.environ.get(parts[0], parts[1] if len(parts) > 1 else "")
                    if hasattr(section_obj, k):
                        current = getattr(section_obj, k)
                        if current is not None and v is not None:
                            setattr(section_obj, k, type(current)(v))
                        elif v is not None:
                            setattr(section_obj, k, v)
    return config
