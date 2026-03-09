"""Адаптер клавиатур с автоматическим fallback.

Приоритет: HTTP client (обход бага) → maxapi (когда баг будет исправлен)
"""
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class KeyboardProvider(ABC):
    """Абстрактный базовый класс для провайдеров клавиатур."""
    
    @abstractmethod
    async def send_with_keyboard(
        self,
        chat_id: int,
        text: str,
        buttons: List[List[Dict[str, str]]],
        **kwargs
    ) -> bool:
        """Отправить сообщение с клавиатурой.
        
        Args:
            chat_id: ID чата
            text: Текст сообщения
            buttons: Двумерный массив кнопок
            **kwargs: Дополнительные параметры
            
        Returns:
            True если отправка успешна, иначе False
        """
        pass


class MaxapiKeyboardProvider(KeyboardProvider):
    """
    Провайдер через библиотеку maxapi.
    Используется когда баг будет исправлен.
    """
    
    def __init__(self, bot):
        self.bot = bot
    
    async def send_with_keyboard(
        self,
        chat_id: int,
        text: str,
        buttons: List[List[Dict[str, str]]],
        **kwargs
    ) -> bool:
        try:
            # Конвертация в Pydantic-модели maxapi
            from keyboards import InlineKeyboardAttachment, InlineKeyboardRow, InlineKeyboardButton
            
            rows = []
            for row in buttons:
                row_buttons = [
                    InlineKeyboardButton(
                        type=btn.get('type', 'callback'),
                        text=btn['text'],
                        payload=btn.get('payload')
                    )
                    for btn in row
                ]
                rows.append(InlineKeyboardRow(buttons=row_buttons))
            
            keyboard = InlineKeyboardAttachment.from_rows(*rows)
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                attachments=[keyboard]
            )
            return True
        except Exception as e:
            logger.error(f"Maxapi provider failed: {e}")
            return False


class HttpClientKeyboardProvider(KeyboardProvider):
    """
    Провайдер через прямые HTTP-запросы.
    Обходит баг валидации maxapi.
    """
    
    def __init__(self, http_client):
        self.http_client = http_client
    
    async def send_with_keyboard(
        self,
        chat_id: int,
        text: str,
        buttons: List[List[Dict[str, str]]],
        **kwargs
    ) -> bool:
        response = await self.http_client.send_message(
            chat_id=chat_id,
            text=text,
            buttons=buttons
        )
        
        if not response.success:
            logger.error(
                f"HTTP provider failed: {response.status_code} — {response.error_message}"
            )
            return False
        
        return True


class KeyboardAdapter:
    """
    Адаптер с автоматическим fallback.
    Приоритет: HTTP client → maxapi
    """
    
    def __init__(self, bot=None, http_client=None, prefer_http: bool = True):
        self.providers: List[KeyboardProvider] = []
        self.prefer_http = prefer_http
        
        if prefer_http and http_client:
            self.providers.append(HttpClientKeyboardProvider(http_client))
        
        if bot:
            self.providers.append(MaxapiKeyboardProvider(bot))
        
        if not prefer_http and http_client:
            self.providers.append(HttpClientKeyboardProvider(http_client))
        
        logger.info(f"KeyboardAdapter initialized with {len(self.providers)} providers")
    
    async def send_with_keyboard(
        self,
        chat_id: int,
        text: str,
        buttons: List[List[Dict[str, str]]],
        **kwargs
    ) -> bool:
        """
        Отправка с автоматическим fallback между провайдерами.
        
        Args:
            chat_id: ID чата
            text: Текст сообщения
            buttons: Двумерный массив кнопок
            **kwargs: Дополнительные параметры
            
        Returns:
            True если хотя бы один провайдер успешно отправил
        """
        for idx, provider in enumerate(self.providers):
            try:
                logger.debug(f"Trying provider {idx + 1}/{len(self.providers)}")
                success = await provider.send_with_keyboard(
                    chat_id=chat_id,
                    text=text,
                    buttons=buttons,
                    **kwargs
                )
                
                if success:
                    logger.info(f"Successfully sent via provider {idx + 1}")
                    return True
                
                logger.warning(f"Provider {idx + 1} failed, trying next...")
                
            except Exception as e:
                logger.error(f"Provider {idx + 1} exception: {e}")
                continue
        
        logger.error("All keyboard providers failed!")
        return False
