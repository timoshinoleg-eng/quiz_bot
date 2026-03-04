# MAX-Квиз 🤖

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Бот-викторина для мессенджера MAX с поддержкой одиночной игры, дуэлей и Premium-подписки.

## 🚀 Быстрый старт

### Требования

- Python 3.10+
- PostgreSQL 15+ (или SQLite для разработки)
- Redis 7+
- Docker и Docker Compose (опционально)

### Установка

1. **Клонируйте репозиторий:**

```bash
git clone https://github.com/timoshinoleg-eng/quiz_bot.git
cd quiz_bot
```

2. **Создайте виртуальное окружение:**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. **Установите зависимости:**

```bash
pip install -r requirements.txt
```

4. **Настройте переменные окружения:**

```bash
cp .env.example .env
# Отредактируйте .env файл
```

5. **Запустите базу данных (через Docker):**

```bash
docker-compose up -d postgres redis
```

6. **Примените миграции:**

```bash
alembic upgrade head
```

7. **Загрузите вопросы:**

```bash
python scripts/load_questions.py --source rubq --file data/rubq.json
```

8. **Запустите бота:**

```bash
python bot.py
```

### Запуск через Docker Compose

```bash
# Полный стек
docker-compose up -d

# Только базы данных
docker-compose up -d postgres redis

# Просмотр логов
docker-compose logs -f bot
```

## 📁 Структура проекта

```
quiz_bot/
├── bot.py                  # Основной файл бота
├── config.py               # Конфигурация
├── db.py                   # Работа с БД
├── models.py               # SQLAlchemy модели
├── states.py               # FSM через БД
├── keyboards.py            # Inline-клавиатуры
├── questions.py            # Загрузка вопросов
├── requirements.txt        # Зависимости
├── docker-compose.yml      # Docker конфигурация
├── Dockerfile              # Сборка образа
├── .env.example            # Пример переменных окружения
├── services/               # Сервисы
│   ├── __init__.py
│   ├── game_logic.py       # Игровая логика
│   ├── duels.py            # Дуэли через Redis
│   └── monetization.py     # Платежи и Premium
├── utils/                  # Утилиты
│   ├── __init__.py
│   └── image_gen.py        # Генерация карточек
├── content/                # Контент
│   ├── __init__.py
│   └── validator.py        # Валидация вопросов
├── tests/                  # Тесты
│   ├── __init__.py
│   ├── test_bot.py
│   ├── test_game.py
│   └── test_validator.py
├── migrations/             # Alembic миграции
│   └── versions/
└── scripts/                # Вспомогательные скрипты
    └── load_questions.py
```

## 🎮 Функционал

### Одиночный режим
- Выбор темы (История, Наука, Спорт, География, Искусство, Развлечения)
- Три уровня сложности
- 5, 10 или 15 вопросов
- Таймер 30 секунд на ответ
- Система жизней (3 ошибки = конец игры)
- Очки с бонусом за скорость

### Дуэли
- Создание дуэли с выбором темы
- Присоединение по ссылке
- Real-time синхронизация через Redis Pub/Sub
- Автоматический подбор соперника (matchmaking)

### Premium
- Без рекламы
- Эксклюзивные категории
- Неограниченные подсказки
- Удвоенные очки
- Интеграция с YooKassa

### Дополнительно
- Daily streaks с наградами
- Таблица лидеров
- Генерация карточек результатов для Stories
- Аналитика событий

## 🗄️ База данных

### Схема

```sql
-- Основные таблицы
users           -- Пользователи
questions       -- Вопросы
games           -- Игровые сессии
game_questions  -- Связь игр и вопросов
duels           -- Дуэли
payments        -- Платежи
analytics_events -- Аналитика
```

### Миграции

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "description"

# Применить миграции
alembic upgrade head

# Откатить миграцию
alembic downgrade -1
```

## 🧪 Тестирование

```bash
# Запуск всех тестов
pytest

# С покрытием
pytest --cov=.

# Конкретный файл
pytest tests/test_game.py

# С детальным выводом
pytest -v
```

## 📊 Мониторинг

### Метрики
- DAU/MAU
- Retention D1/D7/D30
- Completion rate
- K-factor
- ARPU
- CAC

### Логирование

Логи сохраняются в `logs/` и выводятся в stdout:

```bash
# Просмотр логов
tail -f logs/bot.log

# Через Docker
docker-compose logs -f bot
```

## 🔒 Безопасность

### Rate Limiting
- IP: 100 запросов/мин
- User ID: 30 запросов/мин
- Redis sliding window

### Anti-Cheat
- Device fingerprinting
- Анализ паттернов ответов
- Проверка на накрутку

## 🚀 Деплой

### Production Checklist

- [ ] Настроены переменные окружения
- [ ] Создана база данных PostgreSQL
- [ ] Настроен Redis
- [ ] Настроен webhook (рекомендуется)
- [ ] Настроен SSL сертификат
- [ ] Настроен бэкап БД
- [ ] Настроен мониторинг
- [ ] Проверены лимиты API
- [ ] Загружены вопросы
- [ ] Протестированы платежи

### Рекомендуемый стек

- **VPS**: Hetzner, DigitalOcean, AWS
- **БД**: PostgreSQL 15+
- **Кэш**: Redis 7+
- **Прокси**: Nginx
- **SSL**: Let's Encrypt
- **Мониторинг**: Prometheus + Grafana

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте ветку (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📄 Лицензия

Распространяется под лицензией MIT. См. [LICENSE](LICENSE)

## 📞 Поддержка

- Telegram: [@MAX_Quiz_Bot](https://t.me/MAX_Quiz_Bot)
- Email: support@maxquiz.ru
- Issues: [GitHub Issues](https://github.com/yourusername/quiz_bot/issues)

---

<p align="center">
  Made with ❤️ for MAX users
</p>
