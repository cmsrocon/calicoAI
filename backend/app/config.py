from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./ginger.db"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    minimax_api_key: str = ""
    ollama_base_url: str = ""  # defaults to http://localhost:11434/v1 if blank

    # Default LLM config (overridden by app_settings table at runtime)
    default_llm_provider: str = "anthropic"
    default_llm_model: str = "claude-sonnet-4-6"
    environment: str = "development"
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:3000"
    trusted_hosts: str = "localhost,127.0.0.1"
    require_https_cookies: bool = False
    session_ttl_hours: int = 12
    session_idle_timeout_minutes: int = 60
    session_cookie_same_site: str = "lax"
    token_quota_window_days: int = 30
    refresh_cooldown_minutes: int = 30
    superadmin_email: str = ""
    superadmin_password: str = ""
    superadmin_name: str = ""

    def allowed_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_allowed_origins.split(",") if item.strip()]

    def trusted_hosts_list(self) -> list[str]:
        return [item.strip() for item in self.trusted_hosts.split(",") if item.strip()]


settings = Settings()
