"""Fail closed before a production container touches the shared database."""
from __future__ import annotations

import os
import sys
from urllib.parse import urlparse


REQUIRED = (
    "BOT_TOKEN",
    "BOT_USERNAME",
    "BOT_MODE",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_BOT_USERNAME",
    "TELEGRAM_WEBHOOK_URL",
    "TELEGRAM_WEBHOOK_SECRET",
    "MAX_WEBHOOK_URL",
    "MAX_WEBHOOK_SECRET",
    "DATABASE_URL",
    "PG_DSN",
    "APP_SESSION_SECRET",
    "MINI_APP_URL",
    "CORS_ORIGINS",
)


def invalid(value: str) -> bool:
    lowered = value.strip().lower()
    return not lowered or "replace_with" in lowered or "change_me" in lowered or "example" in lowered


def require_https(name: str) -> None:
    value = os.environ[name]
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{name} must be an absolute HTTPS URL")


def main() -> None:
    if os.getenv("ENV") != "production":
        raise ValueError("ENV must equal production")
    missing = [name for name in REQUIRED if invalid(os.getenv(name, ""))]
    if missing:
        raise ValueError("missing or placeholder production settings: " + ", ".join(missing))
    if not os.environ["DATABASE_URL"].startswith(("postgresql://", "postgresql+asyncpg://")):
        raise ValueError("DATABASE_URL must point to PostgreSQL in production")
    if not os.environ["PG_DSN"].startswith("postgresql://"):
        raise ValueError("PG_DSN must be a PostgreSQL client connection string")
    for name in ("MINI_APP_URL", "TELEGRAM_WEBHOOK_URL", "MAX_WEBHOOK_URL"):
        require_https(name)
    if os.environ["BOT_MODE"].lower() != "webhook":
        raise ValueError("BOT_MODE must equal webhook in production")
    print("production preflight: PASS")


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(f"production preflight: FAIL ({error})", file=sys.stderr)
        raise SystemExit(1) from error
