"""Монетизация: Premium-подписки и платежи.

Интеграция с YooKassa для приёма платежей.

Example:
    >>> from services.monetization import PaymentService
    >>> service = PaymentService()
    >>> payment_url = await service.create_payment(user_id, amount)
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import aiohttp

from config import settings
from db import get_db, db_manager
from models import Payment, User


logger = logging.getLogger(__name__)


class PaymentService:
    """Сервис для работы с платежами.
    
    Интеграция с YooKassa API.
    """
    
    YOOKASSA_API_URL = "https://api.yookassa.ru/v3/payments"
    
    def __init__(self):
        """Инициализирует сервис платежей."""
        self.shop_id = settings.PREMIUM.yookassa_shop_id
        self.secret_key = settings.PREMIUM.yookassa_secret_key
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получает или создаёт HTTP сессию.
        
        Returns:
            aiohttp.ClientSession: HTTP сессия
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self) -> None:
        """Закрывает HTTP сессию."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def create_payment(
        self,
        user_id: int,
        amount: float = None,
        currency: str = "RUB",
        description: str = None
    ) -> Dict[str, Any]:
        """Создаёт платёж в YooKassa.
        
        Args:
            user_id: ID пользователя
            amount: Сумма платежа
            currency: Валюта
            description: Описание платежа
            
        Returns:
            Dict: Информация о созданном платеже
        """
        if not self.shop_id or not self.secret_key:
            logger.error("YooKassa credentials not configured")
            return {"error": "Payment provider not configured"}
        
        amount = amount or settings.PREMIUM.price_rub
        description = description or "MAX-Квиз Premium подписка"
        
        # Генерируем уникальный ID платежа
        payment_id = str(uuid.uuid4())
        
        # Формируем данные для YooKassa
        payload = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": currency
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/your_bot?start=payment_success_{payment_id}"
            },
            "description": description,
            "metadata": {
                "user_id": str(user_id),
                "payment_id": payment_id
            }
        }
        
        try:
            session = await self._get_session()
            
            async with session.post(
                self.YOOKASSA_API_URL,
                json=payload,
                auth=aiohttp.BasicAuth(self.shop_id, self.secret_key),
                headers={"Idempotence-Key": payment_id}
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    # Сохраняем платёж в БД
                    await self._save_payment(
                        user_id=user_id,
                        amount=amount,
                        currency=currency,
                        provider_payment_id=data.get("id"),
                        subscription_until=datetime.utcnow() + timedelta(days=30)
                    )
                    
                    confirmation_url = data.get("confirmation", {}).get("confirmation_url")
                    
                    logger.info(f"Payment created for user {user_id}: {data.get('id')}")
                    
                    return {
                        "success": True,
                        "payment_id": payment_id,
                        "provider_payment_id": data.get("id"),
                        "confirmation_url": confirmation_url,
                        "amount": amount,
                        "currency": currency
                    }
                else:
                    logger.error(f"YooKassa error: {data}")
                    return {
                        "success": False,
                        "error": data.get("description", "Unknown error")
                    }
                    
        except Exception as e:
            logger.error(f"Failed to create payment: {e}")
            return {"success": False, "error": str(e)}
    
    async def check_payment(self, provider_payment_id: str) -> Dict[str, Any]:
        """Проверяет статус платежа.
        
        Args:
            provider_payment_id: ID платежа в YooKassa
            
        Returns:
            Dict: Статус платежа
        """
        try:
            session = await self._get_session()
            
            async with session.get(
                f"{self.YOOKASSA_API_URL}/{provider_payment_id}",
                auth=aiohttp.BasicAuth(self.shop_id, self.secret_key)
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    status = data.get("status")
                    
                    # Обновляем статус в БД
                    await self._update_payment_status(provider_payment_id, status)
                    
                    # Если платёж успешен - активируем Premium
                    if status == "succeeded":
                        await self._activate_premium(provider_payment_id)
                    
                    return {
                        "success": True,
                        "status": status,
                        "paid": status == "succeeded"
                    }
                else:
                    return {
                        "success": False,
                        "error": data.get("description", "Unknown error")
                    }
                    
        except Exception as e:
            logger.error(f"Failed to check payment: {e}")
            return {"success": False, "error": str(e)}
    
    async def process_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """Обрабатывает webhook от YooKassa.
        
        Args:
            webhook_data: Данные webhook
            
        Returns:
            bool: True если обработано успешно
        """
        try:
            event = webhook_data.get("event")
            payment_data = webhook_data.get("object", {})
            provider_payment_id = payment_data.get("id")
            status = payment_data.get("status")
            
            logger.info(f"Webhook received: {event} for payment {provider_payment_id}")
            
            # Обновляем статус
            await self._update_payment_status(provider_payment_id, status)
            
            # Активируем Premium при успешном платеже
            if status == "succeeded":
                await self._activate_premium(provider_payment_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process webhook: {e}")
            return False
    
    async def _save_payment(
        self,
        user_id: int,
        amount: float,
        currency: str,
        provider_payment_id: str,
        subscription_until: datetime
    ) -> None:
        """Сохраняет платёж в БД.
        
        Args:
            user_id: ID пользователя
            amount: Сумма
            currency: Валюта
            provider_payment_id: ID в YooKassa
            subscription_until: Дата окончания подписки
        """
        async with get_db() as db:
            payment = Payment(
                user_id=user_id,
                amount=amount,
                currency=currency,
                provider="yookassa",
                provider_payment_id=provider_payment_id,
                status="pending",
                subscription_until=subscription_until
            )
            db.add(payment)
    
    async def _update_payment_status(
        self,
        provider_payment_id: str,
        status: str
    ) -> None:
        """Обновляет статус платежа.
        
        Args:
            provider_payment_id: ID в YooKassa
            status: Новый статус
        """
        async with get_db() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(Payment).where(
                    Payment.provider_payment_id == provider_payment_id
                )
            )
            payment = result.scalar_one_or_none()
            
            if payment:
                payment.status = status
                
                if status == "succeeded":
                    payment.completed_at = datetime.utcnow()
    
    async def _activate_premium(self, provider_payment_id: str) -> None:
        """Активирует Premium для пользователя.
        
        Args:
            provider_payment_id: ID платежа в YooKassa
        """
        async with get_db() as db:
            from sqlalchemy import select
            
            # Получаем платёж
            result = await db.execute(
                select(Payment).where(
                    Payment.provider_payment_id == provider_payment_id
                )
            )
            payment = result.scalar_one_or_none()
            
            if payment and payment.subscription_until:
                # Получаем пользователя
                result = await db.execute(
                    select(User).where(User.id == payment.user_id)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    # Продлеваем Premium
                    current_premium = user.premium_until or datetime.utcnow()
                    
                    if current_premium < datetime.utcnow():
                        current_premium = datetime.utcnow()
                    
                    user.premium_until = current_premium + timedelta(days=30)
                    
                    logger.info(f"Premium activated for user {user.id}")


class PremiumManager:
    """Менеджер для работы с Premium-подпиской."""
    
    @staticmethod
    async def is_premium(user_id: int) -> bool:
        """Проверяет, есть ли у пользователя Premium.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если Premium активен
        """
        return await db_manager.is_premium(user_id)
    
    @staticmethod
    async def get_premium_until(user_id: int) -> Optional[datetime]:
        """Получает дату окончания Premium.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Optional[datetime]: Дата окончания или None
        """
        user = await db_manager.get_or_create_user(user_id)
        return user.premium_until
    
    @staticmethod
    async def get_days_remaining(user_id: int) -> int:
        """Получает количество оставшихся дней Premium.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            int: Количество дней (0 если не Premium)
        """
        premium_until = await PremiumManager.get_premium_until(user_id)
        
        if not premium_until:
            return 0
        
        if premium_until < datetime.utcnow():
            return 0
        
        return (premium_until - datetime.utcnow()).days
    
    @staticmethod
    async def cancel_premium(user_id: int) -> bool:
        """Отменяет Premium подписку.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если успешно
        """
        async with get_db() as db:
            user = await db.get(User, user_id)
            
            if user:
                user.premium_until = datetime.utcnow()
                return True
            
            return False


class AdManager:
    """Менеджер для работы с рекламой."""
    
    def __init__(self):
        """Инициализирует менеджер рекламы."""
        self._ad_counter: Dict[int, int] = {}  # Счётчик вопросов для показа рекламы
    
    def should_show_ad(self, user_id: int, question_index: int) -> bool:
        """Определяет, нужно ли показывать рекламу.
        
        Args:
            user_id: ID пользователя
            question_index: Номер текущего вопроса
            
        Returns:
            bool: True если нужно показать рекламу
        """
        # Не показываем рекламу чаще чем каждые N вопросов
        if question_index > 0 and question_index % settings.GAME.ad_frequency == 0:
            return True
        return False
    
    async def show_rewarded_ad(
        self,
        user_id: int,
        reward_type: str
    ) -> Dict[str, Any]:
        """Показывает rewarded video за награду.
        
        Args:
            user_id: ID пользователя
            reward_type: Тип награды (hint, skip, etc.)
            
        Returns:
            Dict: Результат показа рекламы
        """
        # В реальности здесь интеграция с рекламной сетью
        # Например: AdMob, Unity Ads, ironSource
        
        logger.info(f"Rewarded ad shown to user {user_id}, reward: {reward_type}")
        
        return {
            "success": True,
            "reward": reward_type,
            "message": "Спасибо за просмотр! Ваша награда активирована."
        }
    
    def get_ad_frequency(self) -> int:
        """Получает частоту показа рекламы.
        
        Returns:
            int: Количество вопросов между показами рекламы
        """
        return settings.GAME.ad_frequency


class SubscriptionPlans:
    """Планы подписок."""
    
    PLANS = {
        "monthly": {
            "name": "Premium Monthly",
            "price_rub": 349,
            "price_usd": 3.99,
            "duration_days": 30,
            "features": [
                "Без рекламы",
                "Эксклюзивные категории",
                "Неограниченные подсказки",
                "Удвоенные очки"
            ]
        },
        "yearly": {
            "name": "Premium Yearly",
            "price_rub": 2990,
            "price_usd": 34.99,
            "duration_days": 365,
            "discount": "29%",
            "features": [
                "Всё из Monthly",
                "Эксклюзивные достижения",
                "Приоритетная поддержка"
            ]
        }
    }
    
    @classmethod
    def get_plan(cls, plan_id: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о плане.
        
        Args:
            plan_id: ID плана
            
        Returns:
            Optional[Dict]: Информация о плане
        """
        return cls.PLANS.get(plan_id)
    
    @classmethod
    def get_all_plans(cls) -> Dict[str, Dict[str, Any]]:
        """Получает все планы.
        
        Returns:
            Dict: Все планы
        """
        return cls.PLANS


# Глобальные экземпляры
payment_service = PaymentService()
premium_manager = PremiumManager()
ad_manager = AdManager()
