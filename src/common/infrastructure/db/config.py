__all__ = [
    "Settings",
    "db_settings",
]

from sqlalchemy import Engine, create_engine

import config


class Settings:
    _instance: "Settings | None" = None

    def __new__(cls) -> "Settings":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self.ENGINE: str = config.DB_ENGINE
        self.HOST: str = config.DB_HOST
        self.PORT: int = config.DB_PORT
        self.USER: str = config.DB_USER
        self.PASSWORD: str = config.DB_PASSWORD
        self.DATABASE: str = config.DB_DATABASE

        self.engine: Engine = create_engine(
            self.connection_string,
            pool_size=50,
            max_overflow=10,
            pool_timeout=10,
            pool_recycle=300,
        )

        self._initialized = True

    @property
    def connection_string(self) -> str:
        return (
            f"{self.ENGINE}://{self.USER}:{self.PASSWORD}"
            f"@{self.HOST}:{self.PORT}/{self.DATABASE}"
        )


db_settings: Settings = Settings()
