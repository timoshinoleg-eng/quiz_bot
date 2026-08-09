# Quiz Battle MAX

Закрытая consumer beta быстрой викторины для мессенджера MAX: общий вопрос дня, короткие раунды, вызов друга, XP, streak и недельный рейтинг.

## Реализовано

- `/start` с понятным меню: Daily, быстрая игра, вызов друга, рейтинг и профиль.
- Quick Game на 5/10/15 вопросов с server-side scoring и speed bonus.
- Immutable question set: порядок и варианты ответа фиксируются при создании игры.
- Correct answer не попадает в callback: клиент отправляет только `game_id`, позицию и выбранный индекс.
- Idempotent callback: повторное нажатие не начисляет очки повторно.
- Daily Challenge: один набор на календарный день, одна рейтинговая попытка, streak и место.
- Асинхронный Friend Challenge по коду или MAX deep link, одинаковые вопросы, сравнение и реванш.
- XP, уровни, базовые достижения и weekly leaderboard.
- SQLite для локальной разработки и PostgreSQL для hosted beta.
- Polling для локального beta; webhook оставлен как отдельная transport boundary.

## Быстрый запуск

Требуется Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Заполните BOT_TOKEN в .env
python -m alembic upgrade head
python scripts/load_questions.py --file content/beta_seed.json
python bot.py
```

Для локального режима используется `sqlite+aiosqlite:///./quiz_bot.db`. Для hosted beta задайте `DATABASE_URL` на PostgreSQL и выполните миграции.

## Диагностика MAX-кнопок

При запуске бот пишет подробную трассировку входящих callback-событий, payload кнопок,
доставки клавиатур и ответов MAX API в `logs/quiz_bot.log`. Секреты в лог не записываются.
Для расширенного уровня можно задать `LOG_LEVEL=DEBUG` в `.env`.

## Команды

`/start` — меню; `/daily` — вопрос дня; `/play` — быстрая игра; `/challenge` — создать вызов; `/join CODE` — принять вызов; `/stats` — профиль; `/leaderboard` — рейтинг.

## MAX API

Рабочий HTTP client использует `https://platform-api2.max.ru` и заголовок `Authorization: <BOT_TOKEN>`. Для локальной beta используется polling; переход на webhook не требует переписывания game services.

## Beta limitations

- Платежи, Premium, реклама, Redis realtime, турниры и Mini App выключены.
- Автоматические push-рассылки не выполняются.
- Webhook deployment требует отдельного HTTPS ingress и настройки подписки MAX.
- Существующий backup исходной распакованной копии сохранён вне Git как `quiz_bot-legacy-snapshot-20260809`.

## Проверки

```powershell
python -m compileall -q .
pytest -q
docker compose build
```

## Структура

- `bot.py` — только MAX handlers и transport mapping.
- `db.py` — persistent game operations, idempotency, Daily и challenges.
- `models.py` — SQLAlchemy schema.
- `services/` — game facade, Daily, challenges, profile.
- `content/beta_seed.json` — небольшой проверенный seed.
- `tests/test_beta.py` — acceptance-регрессия beta.
- `docs/BETA_IMPLEMENTATION_REPORT.md` — отчёт и ручной checklist.
