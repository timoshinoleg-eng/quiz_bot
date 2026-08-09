# Quiz Battle MAX — closed beta checklist

## Before a real two-user test

- [ ] Create a MAX bot and put its token only in `.env` as `BOT_TOKEN`.
- [ ] Set `BOT_USERNAME` if deep-link invitations are desired.
- [ ] Use `DEBUG=false` and a private PostgreSQL URL for hosted beta.
- [ ] Run `alembic upgrade head`.
- [ ] Run `python scripts/load_questions.py --file content/beta_seed.json`.
- [ ] Confirm the question count is at least five for every category used.
- [ ] Keep the bot token out of logs, commits and screenshots.

## Local smoke

```powershell
python -m compileall -q .
pytest -q
python bot.py
```

1. `/start` shows Daily, challenge, quick game, ranking and profile.
2. Daily reaches five questions and stores the result.
3. A second Daily click does not create a second ranked attempt.
4. `/challenge` gives a code; `/join CODE` starts the same question set for user B.
5. Duplicate callback does not change score or XP.
6. Restarting the process does not lose Daily or Challenge state.

## Docker beta

```powershell
docker compose build
docker compose up -d postgres
docker compose run --rm bot alembic upgrade head
docker compose run --rm bot python scripts/load_questions.py --file content/beta_seed.json
docker compose up -d bot
docker compose logs -f bot
```

## Explicitly out of scope

Payments, Premium, ads, Redis realtime, tournaments, Mini App, automatic push campaigns and production webhook ingress require separate acceptance work.
