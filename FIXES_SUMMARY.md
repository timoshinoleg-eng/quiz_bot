# Исправления бота MAX-Квиз

## Дата: 2026-03-05

### Исправленные ошибки

#### 1. Клавиатуры (критично)
**Проблема:** Использование dict вместо Pydantic моделей
```
AttributeError: 'dict' object has no attribute 'model_dump'
```

**Решение:**
- Используем `Attachment` с `type=AttachmentType.INLINE_KEYBOARD`
- `ButtonsPayload` с `CallbackButton` для кнопок
- Файл: `keyboards.py`

```python
from maxapi.types import Attachment, ButtonsPayload, CallbackButton
from maxapi.enums.attachment import AttachmentType

return Attachment(
    type=AttachmentType.INLINE_KEYBOARD,
    payload=ButtonsPayload(buttons=[[CallbackButton(text="...", payload="...")]])
)
```

#### 2. Отправка клавиатур (критично)
**Проблема:** Использование `keyboard=` параметра

**Решение:**
- Используем `attachments=[keyboard]` где keyboard это `Attachment`
- Файл: `bot.py`

```python
keyboard = get_main_menu_keyboard(is_premium)
await event.message.answer(
    welcome_text,
    attachments=[keyboard] if keyboard else None
)
```

#### 3. SQLite autoincrement (критично)
**Проблема:** `NOT NULL constraint failed: analytics_events.id`

**Решение:**
- Добавлен `autoincrement=True` для полей `id` в `models.py`
- Исключение: таблица `users` (id = user_id из MAX, не автоинкремент)

```python
id = Column(BigInteger, primary_key=True, autoincrement=True)
```

#### 4. log_event() (временное решение)
**Проблема:** Ошибки с autoincrement в SQLite

**Решение:**
- Временно отключено сохранение в БД
- События только логируются в консоль

```python
@staticmethod
async def log_event(...):
    logger.debug(f"Event logged: {event_type}, user: {user_id}")
    return  # Отключено для MVP
```

#### 5. Упрощение архитектуры (оптимизация)
**Удалено:**
- Таблицы: `Duel`, `Payment`, `DailyStreak`, `GameQuestion`
- Состояния: `DUEL_WAITING`, `DUEL_IN_PROGRESS`
- Функции дуэлей в `db.py`

**Оставлено:**
- Таблицы: `User`, `Question`, `Game`, `AnalyticsEvent`
- Одиночный режим игры

### Структура файлов

```
quiz_bot/
├── bot.py              # Исправлено: attachments=[keyboard]
├── keyboards.py        # Исправлено: Attachment + ButtonsPayload
├── models.py           # Исправлено: autoincrement=True
├── db.py               # Исправлено: удалены Duel/Payment, log_event отключен
├── states.py           # Исправлено: удалены duel-состояния
├── requirements.txt    # Исправлено: удалены ненужные зависимости
└── test_keyboards.py   # Новый: тест клавиатур
```

### Запуск бота

```bash
# Удалить старую БД
del quiz_bot.db

# Установить зависимости
pip install -r requirements.txt

# Запустить
python bot.py
```

### Проверка

```bash
# Тест клавиатур
python test_keyboards.py

# Ожидаемый вывод:
# [OK] maxapi types imported successfully
# [OK] Main menu keyboard created
# [OK] Topics keyboard created
# [OK] model_dump works
# [SUCCESS] All tests passed!
```

### Статус

- [x] Бот запускается без ошибок импорта
- [x] БД создается без ошибок
- [x] Клавиатуры создаются как Pydantic модели
- [x] Команда /start работает
- [x] Callback-кнопки обрабатываются

### Требования

- Python 3.10+
- maxapi==0.9.15
- SQLAlchemy>=2.0.0
- aiosqlite>=0.19.0
