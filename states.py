"""Finite State Machine (FSM) через базу данных.

Поскольку maxapi не имеет встроенной FSM, реализуем её через БД.
Поддерживает состояния и хранилище данных для каждого пользователя.

Example:
    >>> from states import State, FSMContext
    >>> await set_state(user_id, State.SELECT_TOPIC)
    >>> await state.update_data(topic="history")
"""

import logging
from enum import Enum
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

from db import db_manager, get_db
from models import User


logger = logging.getLogger(__name__)


class State(str, Enum):
    """Возможные состояния пользователя в FSM.
    
    Attributes:
        IDLE: Ожидание, не в игре
        SELECT_TOPIC: Выбор темы
        SELECT_DIFFICULTY: Выбор сложности
        SELECT_QUESTION_COUNT: Выбор количества вопросов
        IN_GAME: В процессе игры
        ANSWERING: Ответ на вопрос
        GAME_OVER: Игра завершена
        DUEL_WAITING: Ожидание противника для дуэли
        DUEL_IN_PROGRESS: Дуэль в процессе
        PREMIUM_CHECKOUT: Оформление Premium
    """
    IDLE = "idle"
    SELECT_TOPIC = "select_topic"
    SELECT_DIFFICULTY = "select_difficulty"
    SELECT_QUESTION_COUNT = "select_question_count"
    IN_GAME = "in_game"
    ANSWERING = "answering"
    GAME_OVER = "game_over"
    DUEL_WAITING = "duel_waiting"
    DUEL_IN_PROGRESS = "duel_in_progress"
    PREMIUM_CHECKOUT = "premium_checkout"


@dataclass
class FSMContext:
    """Контекст FSM для пользователя.
    
    Attributes:
        user_id: ID пользователя
        state: Текущее состояние
        data: Данные состояния
    """
    user_id: int
    state: Optional[str]
    data: Dict[str, Any]
    
    async def update_data(self, **kwargs) -> None:
        """Обновляет данные состояния.
        
        Args:
            **kwargs: Ключ-значение для обновления
        """
        self.data.update(kwargs)
        await set_state(self.user_id, self.state, self.data)
    
    async def get_data(self) -> Dict[str, Any]:
        """Получает все данные состояния.
        
        Returns:
            Dict[str, Any]: Данные состояния
        """
        return self.data
    
    async def clear_data(self) -> None:
        """Очищает данные состояния."""
        self.data = {}
        await set_state(self.user_id, self.state, self.data)
    
    async def set_state(self, new_state: Optional[State]) -> None:
        """Устанавливает новое состояние.
        
        Args:
            new_state: Новое состояние
        """
        self.state = new_state.value if new_state else None
        await set_state(self.user_id, self.state, self.data)
    
    async def finish(self) -> None:
        """Завершает FSM, сбрасывает состояние и данные."""
        self.state = None
        self.data = {}
        await set_state(self.user_id, None, {})


async def set_state(
    user_id: int,
    state: Optional[str],
    data: Optional[Dict[str, Any]] = None
) -> None:
    """Устанавливает состояние пользователя.
    
    Args:
        user_id: ID пользователя
        state: Новое состояние
        data: Данные состояния
    """
    await db_manager.update_user_state(user_id, state, data)
    logger.debug(f"User {user_id} state changed to: {state}")


async def get_state(user_id: int) -> Optional[str]:
    """Получает текущее состояние пользователя.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Optional[str]: Текущее состояние или None
    """
    state, _ = await db_manager.get_user_state(user_id)
    return state


async def get_context(user_id: int) -> FSMContext:
    """Получает контекст FSM для пользователя.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        FSMContext: Контекст FSM
    """
    state, data = await db_manager.get_user_state(user_id)
    return FSMContext(user_id=user_id, state=state, data=data or {})


async def reset_state(user_id: int) -> None:
    """Сбрасывает состояние пользователя.
    
    Args:
        user_id: ID пользователя
    """
    await set_state(user_id, None, {})
    logger.info(f"User {user_id} state reset")


def state_filter(*allowed_states: State) -> Callable:
    """Декоратор для фильтрации по состоянию.
    
    Args:
        *allowed_states: Разрешённые состояния
        
    Returns:
        Callable: Декоратор
        
    Example:
        >>> @state_filter(State.IN_GAME)
        ... async def handle_answer(message: Message):
        ...     pass
    """
    def decorator(handler: Callable) -> Callable:
        async def wrapper(message, *args, **kwargs):
            from maxapi.types import Message
            
            user_id = message.from_user.id
            current_state = await get_state(user_id)
            
            if current_state in [s.value for s in allowed_states]:
                return await handler(message, *args, **kwargs)
            else:
                logger.warning(
                    f"User {user_id} tried to access handler in wrong state: "
                    f"{current_state}, allowed: {[s.value for s in allowed_states]}"
                )
                # Можно отправить сообщение о неверном состоянии
                if hasattr(message, 'reply'):
                    await message.reply(
                        "Эта команда недоступна в текущем состоянии. "
                        "Используйте /start для начала."
                    )
                return None
        
        return wrapper
    return decorator


class StateGroup:
    """Базовый класс для группировки состояний.
    
    Example:
        >>> class GameStates(StateGroup):
        ...     SELECT_TOPIC = State.SELECT_TOPIC
        ...     SELECT_DIFFICULTY = State.SELECT_DIFFICULTY
    """
    pass


class GameStates(StateGroup):
    """Состояния игрового процесса."""
    SELECT_TOPIC = State.SELECT_TOPIC
    SELECT_DIFFICULTY = State.SELECT_DIFFICULTY
    SELECT_QUESTION_COUNT = State.SELECT_QUESTION_COUNT
    IN_GAME = State.IN_GAME
    ANSWERING = State.ANSWERING
    GAME_OVER = State.GAME_OVER


class DuelStates(StateGroup):
    """Состояния дуэли."""
    WAITING = State.DUEL_WAITING
    IN_PROGRESS = State.DUEL_IN_PROGRESS
