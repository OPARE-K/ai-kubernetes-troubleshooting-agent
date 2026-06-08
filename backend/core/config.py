from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
    )

    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    kubeconfig_path: str = ""
    insforge_base_url: str = ""
    insforge_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
