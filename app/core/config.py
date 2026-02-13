from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://srochno:password@localhost:5432/srochno"

    # Telegram
    telegram_bot_token: str
    telegram_bot_username: str = ""

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 43200  # 30 days

    # CORS
    cors_origins: str = "http://localhost:10002"

    # Application
    debug: bool = False
    api_prefix: str = "/api"

    # Crypto Bot payments
    crypto_bot_api_token: str = ""
    crypto_bot_network: str = "test"  # "test" | "main"

    # Business logic
    order_lifetime_minutes: int = 60
    no_response_close_minutes: int = 15
    max_executors_per_order: int = 3
    order_take_cost: int = 2  # rubles

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
