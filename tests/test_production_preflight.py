import pytest

from scripts.production_preflight import main


def test_preflight_accepts_complete_production_configuration(monkeypatch):
    values = {
        "ENV": "production",
        "BOT_TOKEN": "max-token",
        "BOT_USERNAME": "quiz_bot",
        "BOT_MODE": "webhook",
        "TELEGRAM_BOT_TOKEN": "telegram-token",
        "TELEGRAM_BOT_USERNAME": "quiz_telegram_bot",
        "TELEGRAM_WEBHOOK_URL": "https://quiz-beta.company.ru/telegram/webhook",
        "TELEGRAM_WEBHOOK_SECRET": "telegram-secret",
        "MAX_WEBHOOK_URL": "https://quiz-beta.company.ru/webhooks/max",
        "MAX_WEBHOOK_SECRET": "max-secret",
        "DATABASE_URL": "postgresql+asyncpg://quiz:password@10.0.0.5:5432/quiz",
        "PG_DSN": "postgresql://quiz:password@10.0.0.5:5432/quiz",
        "APP_SESSION_SECRET": "session-secret",
        "MINI_APP_URL": "https://quiz-beta.company.ru",
        "CORS_ORIGINS": "https://quiz-beta.company.ru",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    main()


def test_preflight_rejects_development_mode(monkeypatch):
    monkeypatch.setenv("ENV", "development")

    with pytest.raises(ValueError, match="ENV must equal production"):
        main()
