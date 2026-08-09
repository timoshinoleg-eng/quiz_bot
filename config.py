"""Configuration for the closed MAX Quiz Battle beta."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BotConfig:
    """Конфигурация бота.
    
    Attributes:
        token: Токен бота от MAX API
        webhook_url: URL для webhook (опционально)
        webhook_path: Путь для webhook
        polling_timeout: Таймаут для long polling
    """
    token: str
    webhook_url: Optional[str] = None
    webhook_path: str = "/webhook"
    polling_timeout: int = 30
    mode: str = "polling"
    username: Optional[str] = None


@dataclass(frozen=True)
class DatabaseConfig:
    """Конфигурация базы данных.
    
    Attributes:
        url: URL подключения к БД
        echo: Логирование SQL запросов
        pool_size: Размер пула соединений
        max_overflow: Максимальное переполнение пула
    """
    url: str
    echo: bool = False
    pool_size: int = 20
    max_overflow: int = 10


@dataclass(frozen=True)
class GameConfig:
    """Конфигурация игровой механики.
    
    Attributes:
        answer_timeout: Время на ответ в секундах
        max_lives: Максимальное количество жизней
        question_options: Доступные варианты количества вопросов
        points_correct: Базовые очки за правильный ответ
        points_speed_bonus: Бонус за скорость ответа
        ad_frequency: Частота показа рекламы (каждые N вопросов)
    """
    answer_timeout: int = 30
    max_lives: int = 3
    question_options: tuple = (5, 10, 15, 20)
    points_correct: int = 100
    points_speed_bonus: int = 50
    daily_question_count: int = 5
    challenge_question_count: int = 5


@dataclass(frozen=True)
class FeatureFlags:
    """Feature flags для включения/отключения функций.
    
    Attributes:
        enable_ads: Reserved for a later product stage
        enable_tournaments: Reserved for a later product stage
        enable_streaks: Включить daily streaks
        enable_analytics: Включить аналитику
    """
    enable_ads: bool = False
    enable_tournaments: bool = False
    enable_streaks: bool = True
    enable_analytics: bool = True


class Settings:
    """Главный класс настроек.
    
    Загружает все конфигурации из переменных окружения.
    """
    
    def __init__(self) -> None:
        """Инициализирует настройки из переменных окружения."""
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.ENV: str = os.getenv("ENV", "development")
        
        # Bot configuration
        self.BOT = BotConfig(
            # BOT_TOKEN is canonical.  MAX_BOT_TOKEN is accepted only as a
            # migration aid for old local .env files.
            token=os.getenv("BOT_TOKEN") or os.getenv("MAX_BOT_TOKEN", ""),
            webhook_url=os.getenv("WEBHOOK_URL"),
            webhook_path=os.getenv("WEBHOOK_PATH", "/webhook"),
            polling_timeout=int(os.getenv("POLLING_TIMEOUT", "30")),
            mode=os.getenv("BOT_MODE", "polling").lower(),
            username=os.getenv("BOT_USERNAME") or None,
        )
        
        # Database configuration
        db_url = os.getenv(
            "DATABASE_URL", 
            "sqlite+aiosqlite:///./quiz_bot.db"
        )
        self.DATABASE = DatabaseConfig(
            url=db_url,
            echo=self.DEBUG,
            pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10"))
        )
        
        # Game configuration
        self.GAME = GameConfig(
            answer_timeout=int(os.getenv("ANSWER_TIMEOUT", "30")),
            max_lives=int(os.getenv("MAX_LIVES", "3")),
            daily_question_count=int(os.getenv("DAILY_QUESTION_COUNT", "5")),
            challenge_question_count=int(os.getenv("CHALLENGE_QUESTION_COUNT", "5"))
        )
        
        # Feature flags
        self.FEATURES = FeatureFlags(
            enable_ads=os.getenv("ENABLE_ADS", "false").lower() == "true",
            enable_streaks=os.getenv("ENABLE_STREAKS", "true").lower() == "true"
        )
        
        # Rate limiting
        self.RATE_LIMIT_IP: int = int(os.getenv("RATE_LIMIT_IP", "100"))
        self.RATE_LIMIT_USER: int = int(os.getenv("RATE_LIMIT_USER", "30"))
        
        # Analytics
        self.ANALYTICS_TOKEN: Optional[str] = os.getenv("ANALYTICS_TOKEN")


# Глобальный экземпляр настроек
settings = Settings()
