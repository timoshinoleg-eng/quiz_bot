# Telegram setup

1. Create a bot in **@BotFather**, keep its token only in `TELEGRAM_BOT_TOKEN`, and set `TELEGRAM_BOT_USERNAME`.
2. In BotFather configure the Main Mini App with the production `MINI_APP_URL` HTTPS origin. It creates the profile **Open App** entry and enables `https://t.me/<bot>?startapp=<opaque-token>` links.
3. Set the Menu Button to the same Mini App URL. Use `/setcommands` (or let `python telegram_bot.py` set them) for `start`, `play`, `daily`, `challenge`, `profile`, `leaderboard`, and `help`.
4. Deploy API and frontend behind HTTPS, set `CORS_ORIGINS` to the exact Mini App origin, and run migrations: `alembic upgrade head`.
5. For a webhook deployment set `TELEGRAM_WEBHOOK_URL` to `https://<api-host>/telegram/webhook`, generate `TELEGRAM_WEBHOOK_SECRET`, and call Bot API `setWebhook` with that exact `secret_token`. The API rejects unsigned/wrong-secret updates; local beta uses `python telegram_bot.py` polling.
6. Test `/start`, the profile Open App button, Menu Button, and `https://t.me/<bot>?startapp=challenge_<opaque-code>` with two separate accounts. Never put user IDs, answers, scores, or secrets in `startapp`.

The backend validates raw `Telegram.WebApp.initData` on every Telegram login. `initDataUnsafe` is UI-only and cannot authenticate an API call.
