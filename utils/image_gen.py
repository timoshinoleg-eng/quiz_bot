"""Генерация карточек результатов для вирусного распространения.

Создаёт изображения для Stories и Link Preview.

Example:
    >>> from utils.image_gen import ResultCardGenerator
    >>> generator = ResultCardGenerator()
    >>> image_path = await generator.generate_stories_card(user_id, score, total)
"""

import io
import logging
import os
from typing import Optional, Tuple
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont


logger = logging.getLogger(__name__)


@dataclass
class CardConfig:
    """Конфигурация карточки.
    
    Attributes:
        width: Ширина изображения
        height: Высота изображения
        bg_color: Цвет фона
        text_color: Цвет текста
        accent_color: Акцентный цвет
    """
    width: int
    height: int
    bg_color: Tuple[int, int, int]
    text_color: Tuple[int, int, int]
    accent_color: Tuple[int, int, int]


# Предустановленные конфигурации
STORIES_CONFIG = CardConfig(
    width=1080,
    height=1920,
    bg_color=(30, 30, 50),
    text_color=(255, 255, 255),
    accent_color=(255, 200, 50)
)

LINK_PREVIEW_CONFIG = CardConfig(
    width=1200,
    height=630,
    bg_color=(30, 30, 50),
    text_color=(255, 255, 255),
    accent_color=(255, 200, 50)
)


class ResultCardGenerator:
    """Генератор карточек результатов."""
    
    def __init__(self, assets_dir: str = "assets"):
        """Инициализирует генератор.
        
        Args:
            assets_dir: Директория с ресурсами (шрифты, логотипы)
        """
        self.assets_dir = assets_dir
        self._fonts: dict = {}
        
        # Создаём директорию для ресурсов если нет
        os.makedirs(assets_dir, exist_ok=True)
    
    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """Получает шрифт нужного размера.
        
        Args:
            size: Размер шрифта
            bold: Жирный шрифт
            
        Returns:
            ImageFont.FreeTypeFont: Шрифт
        """
        font_key = f"{size}_{bold}"
        
        if font_key not in self._fonts:
            # Пробуем загрузить системные шрифты
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",  # Windows
            ]
            
            font = None
            for path in font_paths:
                try:
                    font = ImageFont.truetype(path, size)
                    break
                except:
                    continue
            
            if font is None:
                font = ImageFont.load_default()
            
            self._fonts[font_key] = font
        
        return self._fonts[font_key]
    
    async def generate_stories_card(
        self,
        username: str,
        score: int,
        total: int,
        category: str,
        rank: Optional[int] = None
    ) -> bytes:
        """Генерирует карточку для Instagram/Telegram Stories.
        
        Args:
            username: Имя пользователя
            score: Набранные очки
            total: Максимальные очки
            category: Категория
            rank: Ранг пользователя
            
        Returns:
            bytes: PNG изображение
        """
        config = STORIES_CONFIG
        
        # Создаём изображение
        img = Image.new('RGB', (config.width, config.height), config.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Рисуем градиентный фон
        self._draw_gradient_background(img, config)
        
        # Рисуем логотип
        self._draw_logo(draw, config, y=100)
        
        # Рисуем имя пользователя
        self._draw_text_centered(
            draw,
            f"@{username}",
            y=400,
            font=self._get_font(60),
            color=(200, 200, 200),
            config=config
        )
        
        # Рисуем результат
        result_text = f"{score}/{total}"
        self._draw_text_centered(
            draw,
            result_text,
            y=650,
            font=self._get_font(200, bold=True),
            color=config.accent_color,
            config=config
        )
        
        # Рисуем процент
        percentage = int((score / total) * 100) if total > 0 else 0
        self._draw_text_centered(
            draw,
            f"{percentage}% правильных ответов",
            y=900,
            font=self._get_font(50),
            color=config.text_color,
            config=config
        )
        
        # Рисуем категорию
        self._draw_text_centered(
            draw,
            f"Категория: {category}",
            y=1000,
            font=self._get_font(45),
            color=(180, 180, 180),
            config=config
        )
        
        # Рисуем ранг если есть
        if rank:
            self._draw_text_centered(
                draw,
                f"🏆 Место в топе: #{rank}",
                y=1100,
                font=self._get_font(50),
                color=config.accent_color,
                config=config
            )
        
        # Рисуем CTA
        self._draw_text_centered(
            draw,
            "Сыграй и ты!",
            y=1500,
            font=self._get_font(55),
            color=config.text_color,
            config=config
        )
        
        self._draw_text_centered(
            draw,
            "@MAX_Quiz_Bot",
            y=1600,
            font=self._get_font(70, bold=True),
            color=config.accent_color,
            config=config
        )
        
        # Конвертируем в bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        buffer.seek(0)
        
        return buffer.getvalue()
    
    async def generate_link_preview(
        self,
        username: str,
        score: int,
        total: int,
        category: str
    ) -> bytes:
        """Генерирует карточку для Link Preview (Open Graph).
        
        Args:
            username: Имя пользователя
            score: Набранные очки
            total: Максимальные очки
            category: Категория
            
        Returns:
            bytes: PNG изображение
        """
        config = LINK_PREVIEW_CONFIG
        
        img = Image.new('RGB', (config.width, config.height), config.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Градиентный фон
        self._draw_gradient_background(img, config)
        
        # Логотип слева
        self._draw_logo(draw, config, x=100, y=200)
        
        # Результат справа
        result_text = f"{score}/{total}"
        self._draw_text(
            draw,
            result_text,
            x=700,
            y=200,
            font=self._get_font(150, bold=True),
            color=config.accent_color
        )
        
        # Имя пользователя
        self._draw_text(
            draw,
            f"@{username}",
            x=700,
            y=400,
            font=self._get_font(50),
            color=(200, 200, 200)
        )
        
        # Категория
        self._draw_text(
            draw,
            category,
            x=700,
            y=480,
            font=self._get_font(40),
            color=(180, 180, 180)
        )
        
        # CTA
        self._draw_text_centered(
            draw,
            "Сыграй в MAX-Квиз — @MAX_Quiz_Bot",
            y=550,
            font=self._get_font(45),
            color=config.text_color,
            config=config
        )
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        buffer.seek(0)
        
        return buffer.getvalue()
    
    async def generate_achievement_card(
        self,
        username: str,
        achievement_name: str,
        achievement_description: str,
        rarity: str = "common"
    ) -> bytes:
        """Генерирует карточку достижения.
        
        Args:
            username: Имя пользователя
            achievement_name: Название достижения
            achievement_description: Описание достижения
            rarity: Редкость (common, rare, epic, legendary)
            
        Returns:
            bytes: PNG изображение
        """
        config = STORIES_CONFIG
        
        # Цвета по редкости
        rarity_colors = {
            "common": (150, 150, 150),
            "rare": (50, 150, 255),
            "epic": (200, 50, 255),
            "legendary": (255, 200, 50)
        }
        
        accent = rarity_colors.get(rarity, rarity_colors["common"])
        
        img = Image.new('RGB', (config.width, config.height), config.bg_color)
        draw = ImageDraw.Draw(img)
        
        self._draw_gradient_background(img, config)
        
        # Заголовок
        self._draw_text_centered(
            draw,
            "🏆 НОВОЕ ДОСТИЖЕНИЕ!",
            y=300,
            font=self._get_font(70, bold=True),
            color=accent,
            config=config
        )
        
        # Название достижения
        self._draw_text_centered(
            draw,
            achievement_name,
            y=700,
            font=self._get_font(100, bold=True),
            color=config.text_color,
            config=config
        )
        
        # Описание
        self._draw_text_centered(
            draw,
            achievement_description,
            y=900,
            font=self._get_font(50),
            color=(200, 200, 200),
            config=config
        )
        
        # Пользователь
        self._draw_text_centered(
            draw,
            f"@{username}",
            y=1200,
            font=self._get_font(60),
            color=accent,
            config=config
        )
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        buffer.seek(0)
        
        return buffer.getvalue()
    
    def _draw_gradient_background(
        self,
        img: Image.Image,
        config: CardConfig
    ) -> None:
        """Рисует градиентный фон.
        
        Args:
            img: Изображение
            config: Конфигурация
        """
        draw = ImageDraw.Draw(img)
        
        # Простой градиент сверху вниз
        for y in range(config.height):
            # Интерполяция цвета
            ratio = y / config.height
            r = int(config.bg_color[0] * (1 - ratio * 0.3))
            g = int(config.bg_color[1] * (1 - ratio * 0.3))
            b = int(config.bg_color[2] * (1 - ratio * 0.1))
            
            draw.line([(0, y), (config.width, y)], fill=(r, g, b))
    
    def _draw_logo(
        self,
        draw: ImageDraw.ImageDraw,
        config: CardConfig,
        x: Optional[int] = None,
        y: int = 100
    ) -> None:
        """Рисует логотип.
        
        Args:
            draw: Объект для рисования
            config: Конфигурация
            x: Позиция X (None для центра)
            y: Позиция Y
        """
        text = "MAX-КВИЗ"
        font = self._get_font(80, bold=True)
        
        if x is None:
            self._draw_text_centered(draw, text, y, font, config.accent_color, config)
        else:
            self._draw_text(draw, text, x, y, font, config.accent_color)
    
    def _draw_text_centered(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        y: int,
        font: ImageFont.FreeTypeFont,
        color: Tuple[int, int, int],
        config: CardConfig
    ) -> None:
        """Рисует текст по центру.
        
        Args:
            draw: Объект для рисования
            text: Текст
            y: Позиция Y
            font: Шрифт
            color: Цвет
            config: Конфигурация
        """
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (config.width - text_width) // 2
        draw.text((x, y), text, font=font, fill=color)
    
    def _draw_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        font: ImageFont.FreeTypeFont,
        color: Tuple[int, int, int]
    ) -> None:
        """Рисует текст.
        
        Args:
            draw: Объект для рисования
            text: Текст
            x: Позиция X
            y: Позиция Y
            font: Шрифт
            color: Цвет
        """
        draw.text((x, y), text, font=font, fill=color)
    
    async def save_card(
        self,
        image_bytes: bytes,
        filename: str,
        output_dir: str = "generated_cards"
    ) -> str:
        """Сохраняет карточку в файл.
        
        Args:
            image_bytes: Байты изображения
            filename: Имя файла
            output_dir: Директория для сохранения
            
        Returns:
            str: Путь к файлу
        """
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        
        logger.info(f"Card saved to {filepath}")
        
        return filepath


# Глобальный экземпляр
card_generator = ResultCardGenerator()
