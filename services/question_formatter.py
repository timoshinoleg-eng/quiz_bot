"""Сервис форматирования вопросов и результатов с эмодзи."""
from typing import List, Optional
from keyboards_http import CATEGORY_EMOJIS, DIFFICULTY_EMOJIS


class QuestionFormatter:
    """Форматтер для вопросов и результатов викторины."""
    
    # Эмодзи для достижений
    ACHIEVEMENT_EMOJIS = {
        'perfect': '👑',
        'excellent': '🏆',
        'good': '⭐',
        'average': '👍',
        'try_harder': '💪',
        'poor': '📚'
    }
    
    # Границы процентов для достижений
    ACHIEVEMENT_THRESHOLDS = {
        90: 'perfect',
        70: 'excellent',
        50: 'good',
        30: 'average',
        0: 'try_harder'
    }
    
    @staticmethod
    def format_question_text(
        question_text: str,
        question_number: int,
        total_questions: int,
        category: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> str:
        """
        Форматирует текст вопроса с прогрессом и информацией о категории.
        
        Args:
            question_text: Текст вопроса
            question_number: Номер текущего вопроса (1-based)
            total_questions: Общее количество вопросов
            category: Категория вопроса
            difficulty: Сложность вопроса
            
        Returns:
            Отформатированный текст вопроса
        """
        lines = []
        
        # Заголовок с номером вопроса
        lines.append(f"🎯 <b>Вопрос {question_number}/{total_questions}</b>")
        
        # Информация о категории и сложности
        badges = []
        if category:
            cat_emoji = CATEGORY_EMOJIS.get(category, '❓')
            cat_name = category.capitalize()
            badges.append(f"{cat_emoji} {cat_name}")
        
        if difficulty:
            diff_emoji = DIFFICULTY_EMOJIS.get(difficulty, '⚪')
            diff_name = {
                'EASY': 'Легко',
                'MEDIUM': 'Средне',
                'HARD': 'Сложно'
            }.get(difficulty, difficulty)
            badges.append(f"{diff_emoji} {diff_name}")
        
        if badges:
            lines.append(f"{' | '.join(badges)}")
        
        lines.append("")  # Пустая строка
        lines.append(f"❓ <b>{question_text}</b>")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_result_text(
        score: int,
        total: int,
        category: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> str:
        """
        Форматирует текст результата игры.
        
        Args:
            score: Количество правильных ответов
            total: Общее количество вопросов
            category: Категория игры
            difficulty: Сложность игры
            
        Returns:
            Отформатированный текст результата
        """
        percentage = (score / total * 100) if total > 0 else 0
        
        # Определяем достижение
        achievement = 'poor'
        for threshold, ach in QuestionFormatter.ACHIEVEMENT_THRESHOLDS.items():
            if percentage >= threshold:
                achievement = ach
                break
        
        emoji = QuestionFormatter.ACHIEVEMENT_EMOJIS[achievement]
        
        lines = []
        
        # Заголовок с достижением
        if achievement == 'perfect':
            title = "🎉 ИДЕАЛЬНО! 🎉"
        elif achievement == 'excellent':
            title = "🌟 ВЕЛИКОЛЕПНО! 🌟"
        elif achievement == 'good':
            title = "👍 Отличный результат!"
        elif achievement == 'average':
            title = "⭐ Хорошо!"
        else:
            title = "💪 Попробуй ещё раз!"
        
        lines.append(f"<b>{title}</b>")
        lines.append("")
        
        # Основной счёт
        lines.append(f"{emoji} <b>Правильных ответов:</b> {score}/{total}")
        
        # Процент
        lines.append(f"📊 <b>Точность:</b> {percentage:.1f}%")
        
        # Прогресс-бар
        filled = int(percentage / 10)
        progress_bar = "█" * filled + "░" * (10 - filled)
        lines.append(f"[{progress_bar}] {percentage:.0f}%")
        
        # Дополнительная информация
        info_lines = []
        if category:
            cat_emoji = CATEGORY_EMOJIS.get(category, '❓')
            info_lines.append(f"{cat_emoji} {category.capitalize()}")
        
        if difficulty:
            diff_emoji = DIFFICULTY_EMOJIS.get(difficulty, '⚪')
            diff_name = {
                'EASY': 'Лёгкая',
                'MEDIUM': 'Средняя',
                'HARD': 'Сложная'
            }.get(difficulty, difficulty)
            info_lines.append(f"{diff_emoji} {diff_name} сложность")
        
        if info_lines:
            lines.append("")
            lines.append(" | ".join(info_lines))
        
        # Мотивационное сообщение
        lines.append("")
        if achievement == 'perfect':
            lines.append("🏅 Ты настоящий эксперт! Все ответы верны!")
        elif achievement == 'excellent':
            lines.append("🎯 Почти идеально! Продолжай в том же духе!")
        elif achievement == 'good':
            lines.append("📈 Отличная работа! Есть куда расти!")
        elif achievement == 'average':
            lines.append("🌱 Неплохо! Ещё немного практики!")
        else:
            lines.append("📚 Тренируйся, и результат улучшится!")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_answer_feedback(
        is_correct: bool,
        selected_answer: str,
        correct_answer: str
    ) -> str:
        """
        Форматирует фидбек после ответа.
        
        Args:
            is_correct: Правильный ли ответ
            selected_answer: Выбранный ответ
            correct_answer: Правильный ответ
            
        Returns:
            Отформатированный текст фидбека
        """
        if is_correct:
            emojis = ["✅", "🎉", "👏", "💯", "🌟"]
            messages = [
                "Правильно!",
                "Верно!",
                "Отлично!",
                "Идеально!",
                "Точно!"
            ]
            import random
            return f"{random.choice(emojis)} <b>{random.choice(messages)}</b>\n\n✓ {selected_answer}"
        else:
            return (
                f"❌ <b>Неправильно</b>\n\n"
                f"Твой ответ: {selected_answer}\n"
                f"✅ Правильный: <b>{correct_answer}</b>"
            )
    
    @staticmethod
    def format_stats_text(
        total_games: int,
        total_answers: int,
        correct_answers: int,
        best_category: Optional[str] = None
    ) -> str:
        """
        Форматирует текст статистики.
        
        Args:
            total_games: Общее количество игр
            total_answers: Общее количество ответов
            correct_answers: Количество правильных ответов
            best_category: Лучшая категория
            
        Returns:
            Отформатированный текст статистики
        """
        accuracy = (correct_answers / total_answers * 100) if total_answers > 0 else 0
        
        lines = [
            "📊 <b>Твоя статистика</b>",
            "",
            f"🎮 <b>Всего игр:</b> {total_games}",
            f"❓ <b>Всего вопросов:</b> {total_answers}",
            f"✅ <b>Правильных ответов:</b> {correct_answers}",
            f"📈 <b>Точность:</b> {accuracy:.1f}%",
        ]
        
        if best_category:
            cat_emoji = CATEGORY_EMOJIS.get(best_category, '❓')
            lines.append("")
            lines.append(f"🏆 <b>Сильнейшая категория:</b> {cat_emoji} {best_category.capitalize()}")
        
        # Рейтинговая шкала
        lines.append("")
        if accuracy >= 80:
            rank = "🏅 Мастер"
        elif accuracy >= 60:
            rank = "⭐ Эксперт"
        elif accuracy >= 40:
            rank = "📚 Знаток"
        else:
            rank = "🌱 Новичок"
        
        lines.append(f"🎯 <b>Звание:</b> {rank}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_category_selection_text() -> str:
        """Форматирует текст выбора категории."""
        return (
            "🎯 <b>Выбери категорию</b>\n\n"
            f"{CATEGORY_EMOJIS['HISTORY']} <b>История</b> — события прошлого\n"
            f"{CATEGORY_EMOJIS['SCIENCE']} <b>Наука</b> — физика, химия, биология\n"
            f"{CATEGORY_EMOJIS['GEOGRAPHY']} <b>География</b> — страны и города\n"
            f"{CATEGORY_EMOJIS['SPORT']} <b>Спорт</b> — виды и чемпионы\n"
            f"{CATEGORY_EMOJIS['ART']} <b>Искусство</b> — кино, музыка, живопись\n"
            f"{CATEGORY_EMOJIS['TECHNOLOGY']} <b>Технологии</b> — IT и инновации\n"
            f"{CATEGORY_EMOJIS['NATURE']} <b>Природа</b> — животные и растения\n"
            f"{CATEGORY_EMOJIS['GENERAL']} <b>Общие</b> — разные темы"
        )
    
    @staticmethod
    def format_difficulty_selection_text() -> str:
        """Форматирует текст выбора сложности."""
        return (
            "⚡ <b>Выбери сложность</b>\n\n"
            f"{DIFFICULTY_EMOJIS['EASY']} <b>Легко</b> — для разминки\n"
            f"{DIFFICULTY_EMOJIS['MEDIUM']} <b>Средне</b> — стандартный уровень\n"
            f"{DIFFICULTY_EMOJIS['HARD']} <b>Сложно</b> — для экспертов"
        )
    
    @staticmethod
    def format_question_count_text() -> str:
        """Форматирует текст выбора количества вопросов."""
        return (
            "🔢 <b>Сколько вопросов?</b>\n\n"
            "• 5 — быстрая игра\n"
            "• 10 — стандартная игра\n"
            "• 15 — длительная игра\n"
            "• 20 — марафон знаний"
        )
