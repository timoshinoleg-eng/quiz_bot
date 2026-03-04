"""Тесты для бота.

Тестируют основные хендлеры и команды.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from config import settings
from db import db_manager
from states import State, get_context


@pytest.fixture
def mock_message():
    """Фикстура для мока сообщения."""
    message = MagicMock()
    message.from_user.id = 123456
    message.from_user.username = "test_user"
    message.from_user.first_name = "Test"
    message.reply = AsyncMock()
    return message


@pytest.fixture
def mock_callback():
    """Фикстура для мока callback."""
    callback = MagicMock()
    callback.from_user.id = 123456
    callback.data = "menu:play"
    callback.message = MagicMock()
    callback.message.chat.id = 123456
    callback.message.message_id = 1
    return callback


class TestStartCommand:
    """Тесты команды /start."""
    
    @pytest.mark.asyncio
    async def test_start_new_user(self, mock_message):
        """Тест /start для нового пользователя."""
        with patch("bot.db_manager.get_or_create_user") as mock_get_user:
            mock_get_user.return_value = MagicMock(
                id=123456,
                username="test_user",
                games_played=0,
                score_total=0,
                daily_streak=0
            )
            
            with patch("bot.check_daily_streak") as mock_streak:
                mock_streak.return_value = None
                
                with patch("bot.db_manager.is_premium") as mock_premium:
                    mock_premium.return_value = False
                    
                    # Вызываем хендлер
                    from bot import cmd_start
                    await cmd_start(mock_message)
                    
                    # Проверяем, что reply был вызван
                    assert mock_message.reply.called
                    
                    # Проверяем текст приветствия
                    call_args = mock_message.reply.call_args
                    assert "MAX-Квиз" in call_args[1]["text"]


class TestHelpCommand:
    """Тесты команды /help."""
    
    @pytest.mark.asyncio
    async def test_help_command(self, mock_message):
        """Тест /help."""
        from bot import cmd_help
        await cmd_help(mock_message)
        
        assert mock_message.reply.called
        call_args = mock_message.reply.call_args
        assert "Помощь" in call_args[1]["text"]


class TestStatsCommand:
    """Тесты команды /stats."""
    
    @pytest.mark.asyncio
    async def test_stats_command(self, mock_message):
        """Тест /stats."""
        with patch("bot.db_manager.get_or_create_user") as mock_get_user:
            mock_get_user.return_value = MagicMock(
                games_played=10,
                score_total=5000,
                games_won=7,
                daily_streak=5
            )
            
            from bot import cmd_stats
            await cmd_stats(mock_message)
            
            assert mock_message.reply.called


class TestGameFlow:
    """Тесты игрового процесса."""
    
    @pytest.mark.asyncio
    async def test_topic_selection(self, mock_callback):
        """Тест выбора темы."""
        mock_callback.data = "topic:history"
        
        with patch("bot.bot.edit_message_text") as mock_edit:
            mock_edit.return_value = AsyncMock()
            
            with patch("bot.get_context") as mock_state:
                mock_context = MagicMock()
                mock_context.update_data = AsyncMock()
                mock_context.set_state = AsyncMock()
                mock_state.return_value = mock_context
                
                from bot import process_topic_callback
                await process_topic_callback(mock_callback)
                
                mock_context.update_data.assert_called_once()
                mock_context.set_state.assert_called_once()


class TestPremiumCommand:
    """Тесты команды /premium."""
    
    @pytest.mark.asyncio
    async def test_premium_command(self, mock_message):
        """Тест /premium."""
        from bot import cmd_premium
        await cmd_premium(mock_message)
        
        assert mock_message.reply.called
        call_args = mock_message.reply.call_args
        assert "Premium" in call_args[1]["text"]


class TestStateManagement:
    """Тесты управления состояниями."""
    
    @pytest.mark.asyncio
    async def test_state_transition(self):
        """Тест перехода между состояниями."""
        user_id = 123456
        
        with patch("states.db_manager.update_user_state") as mock_update:
            mock_update.return_value = None
            
            from states import set_state
            await set_state(user_id, State.SELECT_TOPIC)
            
            mock_update.assert_called_once()


class TestKeyboards:
    """Тесты клавиатур."""
    
    def test_main_menu_keyboard(self):
        """Тест главного меню."""
        from keyboards import get_main_menu_keyboard
        
        kb = get_main_menu_keyboard(is_premium=False)
        assert "inline_keyboard" in kb
        assert len(kb["inline_keyboard"]) > 0
    
    def test_topics_keyboard(self):
        """Тест клавиатуры тем."""
        from keyboards import get_topics_keyboard
        
        kb = get_topics_keyboard()
        assert "inline_keyboard" in kb
        
        # Проверяем наличие кнопок категорий
        buttons_text = [btn["text"] for row in kb["inline_keyboard"] for btn in row]
        assert any("История" in text for text in buttons_text)
        assert any("Наука" in text for text in buttons_text)
    
    def test_answers_keyboard(self):
        """Тест клавиатуры ответов."""
        from keyboards import get_answers_keyboard
        
        answers = [("Ответ 1", True), ("Ответ 2", False), ("Ответ 3", False), ("Ответ 4", False)]
        kb = get_answers_keyboard(answers, 0, 1)
        
        assert "inline_keyboard" in kb
        assert len(kb["inline_keyboard"]) == 5  # 4 ответа + подсказка
