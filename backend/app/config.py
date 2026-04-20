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


settings = Settings()
