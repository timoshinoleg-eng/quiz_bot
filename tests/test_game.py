"""Тесты игровой логики.

Тестируют игровую сессию, подсчёт очков, жизни.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from services.game_logic import GameSession, AnswerResult, StreakManager, LeaderboardService
from models import GameStatus


@pytest.fixture
def mock_game():
    """Фикстура для мока игры."""
    game = MagicMock()
    game.id = 1
    game.user_id = 123456
    game.question_count = 10
    game.score = 0
    game.correct_answers = 0
    game.lives_remaining = 3
    game.status = GameStatus.IN_PROGRESS
    return game


@pytest.fixture
def mock_question():
    """Фикстура для мока вопроса."""
    question = MagicMock()
    question.id = 1
    question.text = "Тестовый вопрос?"
    question.correct_answer = "Правильный ответ"
    question.wrong_answers = ["Неправильный 1", "Неправильный 2", "Неправильный 3"]
    return question


class TestGameSession:
    """Тесты игровой сессии."""
    
    @pytest.mark.asyncio
    async def test_game_session_start(self, mock_game):
        """Тест запуска сессии."""
        with patch("services.game_logic.db_manager.get_game") as mock_get_game:
            mock_get_game.return_value = mock_game
            
            with patch("services.game_logic.get_db") as mock_get_db:
                mock_db = MagicMock()
                mock_result = MagicMock()
                mock_result.scalars.return_value.all.return_value = []
                mock_db.execute.return_value = mock_result
                
                async def async_context_manager():
                    return mock_db
                
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=False)
                
                session = GameSession(1, 123456)
                # Тестируем инициализацию
                assert session.game_id == 1
                assert session.user_id == 123456
    
    @pytest.mark.asyncio
    async def test_calculate_points_correct_answer(self):
        """Тест расчёта очков за правильный ответ."""
        session = GameSession(1, 123456)
        
        # Быстрый ответ (полный бонус)
        points, bonus = session._calculate_points(True, 5)
        assert points == 100
        assert bonus > 0
        
        # Медленный ответ (минимальный бонус)
        points, bonus = session._calculate_points(True, 25)
        assert points == 100
        assert bonus >= 0
    
    @pytest.mark.asyncio
    async def test_calculate_points_wrong_answer(self):
        """Тест расчёта очков за неправильный ответ."""
        session = GameSession(1, 123456)
        
        points, bonus = session._calculate_points(False, 5)
        assert points == 0
        assert bonus == 0
    
    @pytest.mark.asyncio
    async def test_submit_correct_answer(self, mock_game, mock_question):
        """Тест отправки правильного ответа."""
        with patch("services.game_logic.db_manager.get_game") as mock_get_game:
            mock_get_game.return_value = mock_game
            
            session = GameSession(1, 123456)
            session.game = mock_game
            session.questions = [mock_question]
            session.current_question_index = 0
            session.question_start_time = datetime.utcnow()
            
            with patch.object(session, "_save_answer_result") as mock_save:
                mock_save.return_value = AsyncMock()
                
                result = await session.submit_answer("Правильный ответ")
                
                assert isinstance(result, AnswerResult)
                assert result.is_correct == True
                assert result.points_earned == 100
                assert result.lives_remaining == 3


class TestStreakManager:
    """Тесты менеджера streaks."""
    
    @pytest.mark.asyncio
    async def test_first_play(self):
        """Тест первой игры."""
        with patch("services.game_logic.db_manager.get_or_create_user") as mock_get_user:
            user = MagicMock()
            user.last_played = None
            user.daily_streak = 0
            mock_get_user.return_value = user
            
            result = await StreakManager.check_streak(123456)
            
            assert result["streak"] == 1
            assert result["reward"] == 10
            assert result["continued"] == False
    
    @pytest.mark.asyncio
    async def test_continue_streak(self):
        """Тест продолжения streak."""
        with patch("services.game_logic.db_manager.get_or_create_user") as mock_get_user:
            user = MagicMock()
            from datetime import timedelta
            user.last_played = datetime.utcnow() - timedelta(days=1)
            user.daily_streak = 2
            mock_get_user.return_value = user
            
            result = await StreakManager.check_streak(123456)
            
            assert result["streak"] == 3
            assert result["continued"] == True
    
    @pytest.mark.asyncio
    async def test_break_streak(self):
        """Тест прерывания streak."""
        with patch("services.game_logic.db_manager.get_or_create_user") as mock_get_user:
            user = MagicMock()
            from datetime import timedelta
            user.last_played = datetime.utcnow() - timedelta(days=3)
            user.daily_streak = 5
            mock_get_user.return_value = user
            
            result = await StreakManager.check_streak(123456)
            
            assert result["streak"] == 1
            assert result["continued"] == False
    
    def test_get_next_milestone(self):
        """Тест получения следующего milestone."""
        assert StreakManager.get_next_milestone(1) == 2
        assert StreakManager.get_next_milestone(3) == 5
        assert StreakManager.get_next_milestone(7) == 14
        assert StreakManager.get_next_milestone(30) == None


class TestLeaderboardService:
    """Тесты сервиса лидерборда."""
    
    @pytest.mark.asyncio
    async def test_get_top_players(self):
        """Тест получения топа игроков."""
        with patch("services.game_logic.get_db") as mock_get_db:
            mock_db = MagicMock()
            
            mock_user1 = MagicMock()
            mock_user1.id = 1
            mock_user1.username = "player1"
            mock_user1.score_total = 10000
            mock_user1.games_played = 50
            
            mock_user2 = MagicMock()
            mock_user2.id = 2
            mock_user2.username = "player2"
            mock_user2.score_total = 8000
            mock_user2.games_played = 40
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_user1, mock_user2]
            mock_db.execute.return_value = mock_result
            
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=False)
            
            players = await LeaderboardService.get_top_players(limit=10)
            
            assert len(players) == 2
            assert players[0]["rank"] == 1
            assert players[0]["username"] == "player1"


class TestGameStats:
    """Тесты статистики игры."""
    
    def test_accuracy_calculation(self):
        """Тест расчёта точности."""
        from services.game_logic import GameStats
        
        stats = GameStats(
            total_questions=10,
            answered_questions=8,
            correct_answers=6,
            total_score=600,
            lives_remaining=2,
            average_time=15.5,
            accuracy=75.0
        )
        
        assert stats.accuracy == 75.0
        assert stats.correct_answers == 6
