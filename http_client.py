"""MAX API HTTP клиент для прямых запросов.

Обходит баг валидации Union-типов в maxapi 0.9.15+.
"""
import aiohttp
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import asyncio
import logging

logger = logging.getLogger(__name__)

MAX_API_BASE = "https://platform-api.max.ru"
MAX_API_VERSION = None  # API doesn't use version prefix


@dataclass
class HttpClientResponse:
    """Ответ HTTP-клиента."""
    success: bool
    status_code: int
    data: Optional[Dict[str, Any]]
    error_message: Optional[str]


class MaxHttpClient:
    """
    Прямой HTTP-клиент для MAX API.
    Обходит баг валидации Union-типов в maxapi 0.9.15+.
    """
    
    def __init__(self, token: str, timeout: int = 30, max_retries: int = 3):
        self.token = token
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazy initialization aiohttp session с connection pooling."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    "Authorization": self.token,
                    "Content-Type": "application/json"
                }
            )
        return self._session
    
    async def close(self):
        """Закрытие сессии (вызывать при shutdown бота)."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        json_payload: Optional[Dict] = None,
        params: Optional[Dict] = None,
        retry_on: List[int] = None
    ) -> HttpClientResponse:
        """
        HTTP-запрос с экспоненциальным backoff.
        
        Args:
            method: HTTP метод (GET, POST, etc.)
            endpoint: API endpoint (без базового URL)
            json_payload: JSON тело запроса
            params: Query параметры URL
            retry_on: Список HTTP статусов для retry (по умолчанию [429, 500, 502, 503, 504])
        """
        if retry_on is None:
            retry_on = [429, 500, 502, 503, 504]
        
        url = f"{MAX_API_BASE}/{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                session = await self._get_session()
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_payload
                ) as response:
                    response_data = await response.json()
                    
                    if response.status < 400:
                        return HttpClientResponse(
                            success=True,
                            status_code=response.status,
                            data=response_data,
                            error_message=None
                        )
                    
                    # Логирование ошибки
                    error_msg = response_data.get('message', 'Unknown error')
                    logger.warning(
                        f"MAX API error: {response.status} — {error_msg} "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    
                    # Retry logic
                    if response.status in retry_on and attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt  # Экспоненциальный backoff
                        logger.info(f"Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    return HttpClientResponse(
                        success=False,
                        status_code=response.status,
                        data=response_data,
                        error_message=error_msg
                    )
                    
            except aiohttp.ClientError as e:
                logger.error(f"Network error: {type(e).__name__}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return HttpClientResponse(
                    success=False,
                    status_code=0,
                    data=None,
                    error_message=f"Network error: {str(e)}"
                )
        
        return HttpClientResponse(
            success=False,
            status_code=0,
            data=None,
            error_message="Max retries exceeded"
        )
    
    async def send_message(
        self,
        chat_id: int,
        text: str,
        buttons: Optional[List[List[Dict[str, str]]]] = None,
        reply_to_message_id: Optional[int] = None,
        disable_notification: bool = False
    ) -> HttpClientResponse:
        """
        Отправка сообщения с inline-клавиатурой.
        
        POST /messages
        Body: {"chat_id": ..., "text": ..., "attachments": [...]}
        
        Args:
            chat_id: ID чата (в теле запроса!)
            text: Текст сообщения (обязательно, до 4096 символов)
            buttons: Двумерный массив кнопок [[{type, text, payload}], ...]
            reply_to_message_id: ID сообщения для ответа
            disable_notification: Отключить уведомление
        
        Returns:
            HttpClientResponse с результатом отправки
        """
        # ✅ ИСПРАВЛЕНО: endpoint без chat_id, chat_id в теле запроса
        endpoint = "messages"
        
        # Тело запроса с chat_id
        json_payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_notification": disable_notification
        }
        
        if reply_to_message_id:
            json_payload["reply_to_message_id"] = reply_to_message_id
        
        if buttons:
            # Валидация структуры кнопок
            if not self._validate_buttons(buttons):
                return HttpClientResponse(
                    success=False,
                    status_code=400,
                    data=None,
                    error_message="Invalid buttons structure"
                )
            
            json_payload["attachments"] = [{
                "type": "inline_keyboard",
                "payload": {"buttons": buttons}
            }]
        
        return await self._request_with_retry(
            method="POST",
            endpoint=endpoint,  # ← просто "messages"
            json_payload=json_payload  # ← chat_id в теле
        )
    
    async def answer_callback_query(
        self,
        callback_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> HttpClientResponse:
        """
        Ответ на callback-запрос (обязательно в течение 10 секунд!).
        
        POST /answers?callback_id={callback_id}
        
        Args:
            callback_id: ID callback из event.callback.callback_id
            text: Текст уведомления (опционально)
            show_alert: Показать как alert (игнорируется в MAX API)
        
        Returns:
            HttpClientResponse с результатом
        """
        # ✅ ИСПРАВЛЕНО: callback_id передается как query параметр (требование API!)
        params = {"callback_id": callback_id}
        
        # ✅ ИСПРАВЛЕНО: ВСЕГДА отправляем notification (требование API!)
        # API требует поле notification или message, иначе ошибка 400
        json_payload = {
            "notification": text or "",  # ← Пустая строка если text=None
            "show_alert": show_alert
        }
        
        return await self._request_with_retry(
            method="POST",
            endpoint="answers",
            params=params,
            json_payload=json_payload
        )
    
    def _validate_buttons(self, buttons: List[List[Dict]]) -> bool:
        """
        Валидация структуры кнопок согласно ограничениям MAX API.
        
        Ограничения:
        - Максимум 30 рядов
        - Максимум 7 кнопок в ряду (для callback)
        - Максимум 210 кнопок всего
        - payload до 64 байт
        - text до 64 символов
        """
        if not isinstance(buttons, list):
            return False
        
        if len(buttons) > 30:
            logger.error(f"Too many rows: {len(buttons)} > 30")
            return False
        
        total_buttons = 0
        for row_idx, row in enumerate(buttons):
            if not isinstance(row, list):
                return False
            
            if len(row) > 7:
                logger.error(f"Row {row_idx}: too many buttons {len(row)} > 7")
                return False
            
            total_buttons += len(row)
            
            for btn_idx, btn in enumerate(row):
                if not isinstance(btn, dict):
                    return False
                
                # Обязательные поля
                if 'type' not in btn or 'text' not in btn:
                    return False
                
                # Валидация text
                if len(btn.get('text', '')) > 64:
                    logger.error(f"Button text too long: {len(btn['text'])} > 64")
                    return False
                
                # Валидация payload для callback
                if btn.get('type') == 'callback':
                    payload = btn.get('payload', '')
                    if len(payload.encode('utf-8')) > 64:
                        logger.error(f"Button payload too long: {len(payload)} > 64 bytes")
                        return False
        
        if total_buttons > 210:
            logger.error(f"Too many buttons: {total_buttons} > 210")
            return False
        
        return True
