import os
from typing import Optional

ENV: str = os.getenv("ENV", "dev")

MAIN_BOT_TOKEN: Optional[str] = os.getenv("MAIN_BOT_TOKEN")

DB_ENGINE: str = os.getenv("DB_ENGINE", "postgresql")
DB_HOST: str = os.getenv("DB_HOST", "localhost" if ENV == "dev" else "")
DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
DB_USER: str = os.getenv("DB_USER", "dev_user" if ENV == "dev" else "")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "12345" if ENV == "dev" else "")
DB_DATABASE: str = os.getenv("DB_DATABASE", "neuroclone_dev" if ENV == "dev" else "")

RABBITMQ_PROTOCOL: str = "amqp" if ENV == "dev" else "amqps"
RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost" if ENV == "dev" else "")
RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest" if ENV == "dev" else "")
RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest" if ENV == "dev" else "")

RABBITMQ_LINK: str = (
    f"{RABBITMQ_PROTOCOL}://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}"
    f"@{RABBITMQ_HOST}:{RABBITMQ_PORT}"
)
