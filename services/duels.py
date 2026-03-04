"""Сервис дуэлей между игроками.

Реализует механику дуэлей через Redis Pub/Sub для real-time взаимодействия.

Example:
    >>> from services.duels import DuelService
    >>> service = DuelService(redis_client)
    >>> duel_id = await service.create_duel(player1_id, category)
"""

import json
import logging
import asyncio
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

import aioredis

from config import settings
from db import get_db, db_manager
from models import Duel, DuelStatus, QuestionCategory, DifficultyLevel, Question
from questions import question_manager


logger = logging.getLogger(__name__)


@dataclass
class DuelState:
    """Состояние дуэли.
    
    Attributes:
        duel_id: ID дуэли
        player1_id: ID первого игрока
        player2_id: ID второго игрока
        current_question: Текущий вопрос (индекс)
        player1_score: Счёт первого игрока
        player2_score: Счёт второго игрока
        player1_answered: Ответил ли первый игрок
        player2_answered: Ответил ли второй игрок
        status: Статус дуэли
    """
    duel_id: int
    player1_id: int
    player2_id: Optional[int] = None
    current_question: int = 0
    player1_score: int = 0
    player2_score: int = 0
    player1_correct: int = 0
    player2_correct: int = 0
    player1_answered: bool = False
    player2_answered: bool = False
    status: str = "waiting"
    questions: List[int] = None
    
    def __post_init__(self):
        if self.questions is None:
            self.questions = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DuelState":
        """Создаёт из словаря."""
        return cls(**data)


class DuelService:
    """Сервис для управления дуэлями.
    
    Использует Redis для real-time синхронизации состояния.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """Инициализирует сервис дуэлей.
        
        Args:
            redis_url: URL подключения к Redis
        """
        self.redis_url = redis_url or f"redis://{settings.REDIS.host}:{settings.REDIS.port}/{settings.REDIS.db}"
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub: Optional[aioredis.client.PubSub] = None
        self._handlers: Dict[str, List[Callable]] = {}
    
    async def connect(self) -> None:
        """Подключается к Redis."""
        self._redis = await aioredis.from_url(
            self.redis_url,
            password=settings.REDIS.password,
            decode_responses=True
        )
        self._pubsub = self._redis.pubsub()
        logger.info("Connected to Redis for duels")
    
    async def disconnect(self) -> None:
        """Отключается от Redis."""
        if self._pubsub:
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
        logger.info("Disconnected from Redis")
    
    async def create_duel(
        self,
        player1_id: int,
        category: QuestionCategory,
        question_count: int = 5,
        difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    ) -> int:
        """Создаёт новую дуэль.
        
        Args:
            player1_id: ID создателя
            category: Категория вопросов
            question_count: Количество вопросов
            difficulty: Сложность
            
        Returns:
            int: ID созданной дуэли
        """
        # Создаём в БД
        duel = await db_manager.create_duel(player1_id, category, question_count)
        
        # Получаем вопросы
        questions = await question_manager.get_questions_for_game(
            category=category,
            difficulty=difficulty,
            count=question_count
        )
        
        question_ids = [q.id for q in questions]
        
        # Создаём состояние в Redis
        state = DuelState(
            duel_id=duel.id,
            player1_id=player1_id,
            questions=question_ids,
            status="waiting"
        )
        
        await self._save_state(duel.id, state)
        
        # Публикуем событие создания
        await self._publish_event(duel.id, {
            "type": "duel_created",
            "duel_id": duel.id,
            "player1_id": player1_id,
            "category": category.value
        })
        
        logger.info(f"Duel {duel.id} created by player {player1_id}")
        
        return duel.id
    
    async def join_duel(self, duel_id: int, player2_id: int) -> bool:
        """Присоединяет второго игрока к дуэли.
        
        Args:
            duel_id: ID дуэли
            player2_id: ID присоединяющегося игрока
            
        Returns:
            bool: True если успешно
        """
        state = await self._get_state(duel_id)
        
        if not state or state.player2_id is not None:
            return False
        
        if state.player1_id == player2_id:
            return False  # Нельзя играть с самим собой
        
        # Обновляем состояние
        state.player2_id = player2_id
        state.status = "in_progress"
        
        await self._save_state(duel_id, state)
        
        # Обновляем в БД
        success = await db_manager.join_duel(duel_id, player2_id)
        
        if success:
            # Публикуем событие начала
            await self._publish_event(duel_id, {
                "type": "duel_started",
                "duel_id": duel_id,
                "player1_id": state.player1_id,
                "player2_id": player2_id
            })
            
            logger.info(f"Player {player2_id} joined duel {duel_id}")
        
        return success
    
    async def submit_answer(
        self,
        duel_id: int,
        player_id: int,
        answer: str,
        is_correct: bool
    ) -> Dict[str, Any]:
        """Обрабатывает ответ игрока в дуэли.
        
        Args:
            duel_id: ID дуэли
            player_id: ID игрока
            answer: Ответ
            is_correct: Правильный ли ответ
            
        Returns:
            Dict: Результат и статус дуэли
        """
        state = await self._get_state(duel_id)
        
        if not state or state.status != "in_progress":
            return {"error": "Duel not found or not in progress"}
        
        # Обновляем счёт
        points = 100 if is_correct else 0
        
        if player_id == state.player1_id:
            state.player1_score += points
            if is_correct:
                state.player1_correct += 1
            state.player1_answered = True
        elif player_id == state.player2_id:
            state.player2_score += points
            if is_correct:
                state.player2_correct += 1
            state.player2_answered = True
        else:
            return {"error": "Player not in this duel"}
        
        await self._save_state(duel_id, state)
        
        # Публикуем событие ответа
        await self._publish_event(duel_id, {
            "type": "player_answered",
            "duel_id": duel_id,
            "player_id": player_id,
            "is_correct": is_correct
        })
        
        # Проверяем, ответили ли оба
        if state.player1_answered and state.player2_answered:
            await self._next_question(duel_id)
        
        return {
            "success": True,
            "player1_score": state.player1_score,
            "player2_score": state.player2_score,
            "both_answered": state.player1_answered and state.player2_answered
        }
    
    async def _next_question(self, duel_id: int) -> None:
        """Переходит к следующему вопросу.
        
        Args:
            duel_id: ID дуэли
        """
        state = await self._get_state(duel_id)
        
        if not state:
            return
        
        state.current_question += 1
        state.player1_answered = False
        state.player2_answered = False
        
        # Проверяем конец дуэли
        if state.current_question >= len(state.questions):
            await self._finish_duel(duel_id)
        else:
            await self._save_state(duel_id, state)
            
            # Публикуем событие нового вопроса
            await self._publish_event(duel_id, {
                "type": "next_question",
                "duel_id": duel_id,
                "question_index": state.current_question,
                "question_id": state.questions[state.current_question]
            })
    
    async def _finish_duel(self, duel_id: int) -> None:
        """Завершает дуэль.
        
        Args:
            duel_id: ID дуэли
        """
        state = await self._get_state(duel_id)
        
        if not state:
            return
        
        # Определяем победителя
        winner_id = None
        if state.player1_score > state.player2_score:
            winner_id = state.player1_id
        elif state.player2_score > state.player1_score:
            winner_id = state.player2_id
        
        state.status = "completed"
        await self._save_state(duel_id, state)
        
        # Обновляем в БД
        async with get_db() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(Duel).where(Duel.id == duel_id)
            )
            duel = result.scalar_one_or_none()
            
            if duel:
                duel.status = DuelStatus.COMPLETED
                duel.player1_score = state.player1_score
                duel.player2_score = state.player2_score
                duel.player1_correct = state.player1_correct
                duel.player2_correct = state.player2_correct
                duel.winner_id = winner_id
                duel.completed_at = datetime.utcnow()
        
        # Публикуем событие завершения
        await self._publish_event(duel_id, {
            "type": "duel_finished",
            "duel_id": duel_id,
            "winner_id": winner_id,
            "player1_score": state.player1_score,
            "player2_score": state.player2_score
        })
        
        logger.info(f"Duel {duel_id} finished. Winner: {winner_id}")
    
    async def get_duel_state(self, duel_id: int) -> Optional[DuelState]:
        """Получает состояние дуэли.
        
        Args:
            duel_id: ID дуэли
            
        Returns:
            Optional[DuelState]: Состояние дуэли
        """
        return await self._get_state(duel_id)
    
    async def get_current_question(self, duel_id: int) -> Optional[Question]:
        """Получает текущий вопрос дуэли.
        
        Args:
            duel_id: ID дуэли
            
        Returns:
            Optional[Question]: Текущий вопрос
        """
        state = await self._get_state(duel_id)
        
        if not state or state.current_question >= len(state.questions):
            return None
        
        question_id = state.questions[state.current_question]
        
        async with get_db() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(Question).where(Question.id == question_id)
            )
            return result.scalar_one_or_none()
    
    async def abandon_duel(self, duel_id: int, player_id: int) -> bool:
        """Игрок покидает дуэль.
        
        Args:
            duel_id: ID дуэли
            player_id: ID игрока
            
        Returns:
            bool: True если успешно
        """
        state = await self._get_state(duel_id)
        
        if not state:
            return False
        
        # Определяем победителя (тот кто остался)
        winner_id = None
        if player_id == state.player1_id:
            winner_id = state.player2_id
        elif player_id == state.player2_id:
            winner_id = state.player1_id
        
        state.status = "abandoned"
        await self._save_state(duel_id, state)
        
        # Публикуем событие
        await self._publish_event(duel_id, {
            "type": "duel_abandoned",
            "duel_id": duel_id,
            "player_id": player_id,
            "winner_id": winner_id
        })
        
        return True
    
    async def list_waiting_duels(
        self,
        category: Optional[QuestionCategory] = None
    ) -> List[Dict[str, Any]]:
        """Получает список ожидающих дуэлей.
        
        Args:
            category: Фильтр по категории
            
        Returns:
            List[Dict]: Список дуэлей
        """
        async with get_db() as db:
            from sqlalchemy import select
            
            query = select(Duel).where(Duel.status == DuelStatus.WAITING)
            
            if category:
                query = query.where(Duel.category == category)
            
            result = await db.execute(query.order_by(Duel.created_at.desc()))
            duels = result.scalars().all()
            
            return [
                {
                    "id": d.id,
                    "player1_id": d.player1_id,
                    "category": d.category.value,
                    "question_count": d.question_count,
                    "created_at": d.created_at.isoformat()
                }
                for d in duels
            ]
    
    # Приватные методы для работы с Redis
    
    def _get_state_key(self, duel_id: int) -> str:
        """Генерирует ключ для хранения состояния.
        
        Args:
            duel_id: ID дуэли
            
        Returns:
            str: Ключ Redis
        """
        return f"duel:state:{duel_id}"
    
    def _get_channel_key(self, duel_id: int) -> str:
        """Генерирует ключ канала Pub/Sub.
        
        Args:
            duel_id: ID дуэли
            
        Returns:
            str: Ключ канала
        """
        return f"duel:channel:{duel_id}"
    
    async def _save_state(self, duel_id: int, state: DuelState) -> None:
        """Сохраняет состояние в Redis.
        
        Args:
            duel_id: ID дуэли
            state: Состояние
        """
        if not self._redis:
            await self.connect()
        
        key = self._get_state_key(duel_id)
        await self._redis.setex(
            key,
            timedelta(hours=2),  # TTL 2 часа
            json.dumps(state.to_dict())
        )
    
    async def _get_state(self, duel_id: int) -> Optional[DuelState]:
        """Получает состояние из Redis.
        
        Args:
            duel_id: ID дуэли
            
        Returns:
            Optional[DuelState]: Состояние или None
        """
        if not self._redis:
            await self.connect()
        
        key = self._get_state_key(duel_id)
        data = await self._redis.get(key)
        
        if data:
            return DuelState.from_dict(json.loads(data))
        
        return None
    
    async def _publish_event(self, duel_id: int, event: Dict[str, Any]) -> None:
        """Публикует событие в канал.
        
        Args:
            duel_id: ID дуэли
            event: Событие
        """
        if not self._redis:
            await self.connect()
        
        channel = self._get_channel_key(duel_id)
        await self._redis.publish(channel, json.dumps(event))
    
    async def subscribe_to_duel(
        self,
        duel_id: int,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Подписывается на события дуэли.
        
        Args:
            duel_id: ID дуэли
            callback: Функция обратного вызова
        """
        if not self._pubsub:
            await self.connect()
        
        channel = self._get_channel_key(duel_id)
        await self._pubsub.subscribe(channel)
        
        # Запускаем обработку сообщений
        asyncio.create_task(self._listen_for_events(callback))
    
    async def _listen_for_events(
        self,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Слушает события из Pub/Sub.
        
        Args:
            callback: Функция обратного вызова
        """
        async for message in self._pubsub.listen():
            if message["type"] == "message":
                try:
                    event = json.loads(message["data"])
                    await callback(event)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode event: {message['data']}")


class DuelMatchmaking:
    """Система матчмейкинга для дуэлей.
    
    Автоматически подбирает соперников по рейтингу.
    """
    
    def __init__(self, duel_service: DuelService):
        """Инициализирует матчмейкинг.
        
        Args:
            duel_service: Сервис дуэлей
        """
        self.duel_service = duel_service
        self._queue: Dict[QuestionCategory, List[int]] = {}
    
    async def join_queue(
        self,
        player_id: int,
        category: QuestionCategory
    ) -> Optional[int]:
        """Добавляет игрока в очередь.
        
        Args:
            player_id: ID игрока
            category: Категория
            
        Returns:
            Optional[int]: ID дуэли если найден соперник
        """
        if category not in self._queue:
            self._queue[category] = []
        
        # Ищем соперника
        for opponent_id in self._queue[category]:
            if opponent_id != player_id:
                self._queue[category].remove(opponent_id)
                
                # Создаём дуэль
                duel_id = await self.duel_service.create_duel(
                    player1_id=opponent_id,
                    category=category
                )
                
                # Присоединяем текущего игрока
                await self.duel_service.join_duel(duel_id, player_id)
                
                return duel_id
        
        # Добавляем в очередь
        if player_id not in self._queue[category]:
            self._queue[category].append(player_id)
        
        return None
    
    async def leave_queue(self, player_id: int, category: QuestionCategory) -> bool:
        """Удаляет игрока из очереди.
        
        Args:
            player_id: ID игрока
            category: Категория
            
        Returns:
            bool: True если был удалён
        """
        if category in self._queue and player_id in self._queue[category]:
            self._queue[category].remove(player_id)
            return True
        return False


# Глобальный экземпляр сервиса дуэлей
duel_service = DuelService()
