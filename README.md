# Quiz Battle

Consumer beta with shared MAX and Telegram entries: one Mini App catalog, rounds, Daily, challenges, XP, streak and leaderboard.

## Platforms

- ✅ MAX
- ✅ Telegram Mini App/backend transport (BotFather URL, HTTPS webhook and two-account live smoke remain deployment gates)

## Реализовано

- React Mini App (`frontend/`) с Home, каталогом из 10 packs, игровым экраном, результатом и sharing fallback.
- FastAPI `/api/v1` для каталога, content stats, профиля и server-authoritative игр.
- 550 V2 RU content records через `python -m scripts.content.bootstrap`; `python -m scripts.content.audit` требует не менее 500 active RU вопросов.
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
# Заполните BOT_TOKEN и APP_SESSION_SECRET в .env
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m scripts.content.bootstrap
.\.venv\Scripts\python -m scripts.content.audit
.\.venv\Scripts\python -m uvicorn api:app --reload
# Отдельно: cd frontend; npm install; npm run dev
```

Для локального режима используется `sqlite+aiosqlite:///./quiz_bot.db`. Для hosted beta задайте `DATABASE_URL` на PostgreSQL и выполните миграции.

## Диагностика MAX-кнопок

При запуске бот пишет подробную трассировку входящих callback-событий, payload кнопок,
доставки клавиатур и ответов MAX API в `logs/quiz_bot.log`. Секреты в лог не записываются.
Для расширенного уровня можно задать `LOG_LEVEL=DEBUG` в `.env`.

## Команды

MAX: `/start` — меню; `/daily` — вопрос дня; `/play` — быстрая игра; `/challenge` — создать вызов; `/join CODE` — принять вызов; `/stats` — профиль; `/leaderboard` — рейтинг.

Telegram: run `python telegram_bot.py` for the thin polling transport. It supports `/start`, `/play`, `/daily`, `/challenge`, `/profile`, `/leaderboard`, `/help`; setup is in [docs/TELEGRAM_SETUP.md](docs/TELEGRAM_SETUP.md).

## MAX API

Рабочий HTTP client использует `https://platform-api2.max.ru` и заголовок `Authorization: <BOT_TOKEN>`. Для локальной beta используется polling; переход на webhook не требует переписывания game services.

## V2 deployment gates

- Mini App требует HTTPS и регистрации URL в MAX Partner Cabinet; до этого бот сохраняет текстовый fallback.
- Production принимает только подписанный MAX `initData`; `X-Development-User` работает лишь при `ENV=development`.
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
