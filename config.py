"""Конфигурация бота MAX-Квиз.

Этот модуль содержит все настройки, токены и feature flags для бота.
Использует pydantic для валидации переменных окружения.

Example:
    >>> from config import settings
    >>> print(settings.BOT_TOKEN)
"""

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
class RedisConfig:
    """Конфигурация Redis.
    
    Attributes:
        host: Хост Redis
        port: Порт Redis
        db: Номер базы данных
        password: Пароль (опционально)
    """
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None


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
    question_options: tuple = (5, 10, 15)
    points_correct: int = 100
    points_speed_bonus: int = 50
    ad_frequency: int = 3


@dataclass(frozen=True)
class PremiumConfig:
    """Конфигурация Premium-подписки.
    
    Attributes:
        price_rub: Цена в рублях
        price_usd: Цена в долларах
        duration_days: Длительность подписки в днях
        yookassa_shop_id: ID магазина YooKassa
        yookassa_secret_key: Секретный ключ YooKassa
    """
    price_rub: int = 349
    price_usd: float = 3.99
    duration_days: int = 30
    yookassa_shop_id: Optional[str] = None
    yookassa_secret_key: Optional[str] = None


@dataclass(frozen=True)
class FeatureFlags:
    """Feature flags для включения/отключения функций.
    
    Attributes:
        enable_ads: Включить рекламу
        enable_premium: Включить Premium-подписку
        enable_duels: Включить режим дуэлей
        enable_tournaments: Включить турниры
        enable_streaks: Включить daily streaks
        enable_analytics: Включить аналитику
    """
    enable_ads: bool = True
    enable_premium: bool = True
    enable_duels: bool = True
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
            token=os.getenv("BOT_TOKEN", ""),
            webhook_url=os.getenv("WEBHOOK_URL"),
            webhook_path=os.getenv("WEBHOOK_PATH", "/webhook"),
            polling_timeout=int(os.getenv("POLLING_TIMEOUT", "30"))
        )
        
        # Database configuration
        db_url = os.getenv(
            "DATABASE_URL", 
            "postgresql+asyncpg://quiz_user:quiz_pass@localhost/quiz_db"
        )
        self.DATABASE = DatabaseConfig(
            url=db_url,
            echo=self.DEBUG,
            pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10"))
        )
        
        # Redis configuration
        self.REDIS = RedisConfig(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD")
        )
        
        # Game configuration
        self.GAME = GameConfig(
            answer_timeout=int(os.getenv("ANSWER_TIMEOUT", "30")),
            max_lives=int(os.getenv("MAX_LIVES", "3")),
            ad_frequency=int(os.getenv("AD_FREQUENCY", "3"))
        )
        
        # Premium configuration
        self.PREMIUM = PremiumConfig(
            price_rub=int(os.getenv("PREMIUM_PRICE_RUB", "349")),
            price_usd=float(os.getenv("PREMIUM_PRICE_USD", "3.99")),
            yookassa_shop_id=os.getenv("YOOKASSA_SHOP_ID"),
            yookassa_secret_key=os.getenv("YOOKASSA_SECRET_KEY")
        )
        
        # Feature flags
        self.FEATURES = FeatureFlags(
            enable_ads=os.getenv("ENABLE_ADS", "true").lower() == "true",
            enable_premium=os.getenv("ENABLE_PREMIUM", "true").lower() == "true",
            enable_duels=os.getenv("ENABLE_DUELS", "true").lower() == "true",
            enable_streaks=os.getenv("ENABLE_STREAKS", "true").lower() == "true"
        )
        
        # Rate limiting
        self.RATE_LIMIT_IP: int = int(os.getenv("RATE_LIMIT_IP", "100"))
        self.RATE_LIMIT_USER: int = int(os.getenv("RATE_LIMIT_USER", "30"))
        
        # Analytics
        self.ANALYTICS_TOKEN: Optional[str] = os.getenv("ANALYTICS_TOKEN")


# Глобальный экземпляр настроек
settings = Settings()
