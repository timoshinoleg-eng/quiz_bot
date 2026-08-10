# Telegram implementation report

## Before

The repository had a MAX-only transport, signed MAX Mini App login, shared SQL game engine, React Mini App V2, 10 packs and 550 active Russian questions. It had no Telegram identity, initData validation, Bot API transport or Telegram bridge.

## Shared vs Telegram-specific

Shared unchanged: questions/packs, immutable games, server-authoritative timing and scoring, Daily/streak, XP, history, challenges and leaderboard. `PlatformIdentity` maps each platform's external ID to the shared player record, so Telegram and MAX numeric IDs cannot collide.

Telegram-only: `telegram_auth.py` validates raw `Telegram.WebApp.initData`; `telegram_bot.py` is a deliberately thin Bot API adapter; the frontend bridge contains the Telegram BackButton, haptic, fullscreen and share/deep-link affordances. Telegram URLs contain only an opaque challenge code.

## Bot and Mini App

The bot supports `/start`, `/play`, `/daily`, `/challenge`, `/profile`, `/leaderboard`, `/help`. It gives Main Mini App buttons; the Mini App has Home, Catalog, Quick Game, Daily, game/result, profile and leaderboard screens. `VITE_PLATFORM=mock` keeps browser development server-side mock-auth only; non-mock builds use signed platform initData.

Telegram integration follows the official Mini Apps validation flow (HMAC key derived from `WebAppData`, sorted data-check string, constant-time comparison and bounded `auth_date`): [Telegram Mini Apps](https://core.telegram.org/bots/webapps). Main Mini Apps, `startapp`, safe-area/theme behavior, BackButton, HapticFeedback and fullscreen are documented there; Bot API sharing-prepared-message capability is documented in [Bot API](https://core.telegram.org/bots/api).

## Content and retention

The single bank has 550 active Russian questions in 10 packs. Daily is immutable per date; the same challenge question set is used by both players. User history remains unseen-first, then incorrect/recently unseen; XP, streaks, achievements, mastery and the weekly leaderboard are common core behavior.

## Tests and CI evidence

- `pytest tests -q`: **12 passed, 0 failed**.
- `python -m compileall -q .`: pass.
- `npm --prefix frontend run build`: pass.
- `git diff --check`: pass.
- Docker build: not run in this session because Docker Desktop is not available; it remains a release gate.

The Telegram tests cover valid initData, forged user ID/signature, expired auth date and collision-free MAX/Telegram identities. Existing suite covers immutable rounds, duplicate answer idempotency, no leaked answer index, Daily/streak, challenges and MAX start handling.

## Known issues / manual acceptance

1. BotFather Main Mini App/Menu Button and production HTTPS/webhook need owner-side configuration with a real Telegram bot token.
2. Two-account Telegram challenge/share/rematch smoke has not run; share uses Telegram deep-link fallback and needs the production `VITE_TELEGRAM_BOT_USERNAME`.
3. Group Battle is not implemented; it is intentionally deferred after personal challenge live acceptance.
4. Content audit still reports editorial duplicate candidates from V2; dedupe before public beta.
5. Docker image build and MAX live regression smoke remain unavailable in this local environment.

Manual test order: `/start` → Open App → Quick Game → another pack → Daily → create challenge → finish → share link → open it as account B → finish → inspect comparison/rematch → repeat in light/dark/mobile/desktop layouts.
