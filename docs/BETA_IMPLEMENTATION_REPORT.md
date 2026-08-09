# MAX Quiz Battle — beta implementation report

## 1. Executive summary

The repository now has a small, persistent consumer-beta core: Quick Game, one shared Daily Challenge per calendar day, asynchronous Friend Challenge, XP/streak/profile and weekly ranking. MAX handlers are transport-only; scoring and state transitions are database operations.

## 2. Architecture

- `bot.py`: MAX event extraction, commands, callbacks and user-facing messages.
- `db.py`: SQLite/PostgreSQL persistence, immutable question sets, callback idempotency and progression awards.
- `models.py`: `GameQuestion`, `DailyChallenge`, `DailyResult`, `FriendChallenge`, `ChallengeQuestion` and `ChallengeAttempt`.
- `services/`: Daily/challenge/profile facades and a compatibility `GameSession`.
- `http_client.py`: current MAX API v2 host, Authorization header, message and callback requests.

## 3. Fixed P0 issues

- Removed the correct answer from callback payloads.
- Fixed question count persistence and no longer reselects questions on every callback.
- Added server-side answer validation, scoring, lives and completion.
- Added duplicate callback idempotency.
- Replaced the mismatched models/migration with one beta schema.
- Unified `BOT_TOKEN` as canonical source, with a temporary `MAX_BOT_TOKEN` read fallback.
- Disabled Premium/payment/ad UI and removed runtime Redis duel/payment implementations.
- Updated `platform-api.max.ru` to `platform-api2.max.ru`, query target parameters and callback acknowledgement shape.

## 4. Gameplay

Quick Game starts after topic, difficulty and count selection. Daily uses one persisted question-id set per UTC date and one ranked result per user. Friend Challenge creates a code/deep link, starts the creator immediately, and lets a second user join asynchronously with the same question ids. A completed pair exposes a rematch action.

## 5. Retention

Daily completion updates current/best streak; completion awards XP and levels; achievements currently include first game, perfect round, 3-day streak and 7-day streak. Weekly leaderboard aggregates completed Daily scores from the current UTC week.

## 6. MAX integration

The verified current documentation uses `https://platform-api2.max.ru`, `Authorization: <token>`, `/messages?chat_id=...`, `/answers?callback_id=...`, inline keyboards and bot deep links `https://max.ru/<bot>?start=<payload>`. Local beta remains polling; webhook is intentionally a separate deployment gate.

## 7. Database

The canonical first migration creates the same tables used by SQLAlchemy metadata. PostgreSQL is the hosted target; SQLite is supported for local beta. `GameQuestion.correct_index` is server-only and `answer_options` is a persisted immutable snapshot.

## 8. Content

`content/beta_seed.json` contains 30 short, child-friendly questions across general knowledge, history, science, sport, geography, art and entertainment. The loader rejects missing answers, duplicate answer options and invalid shapes.

## 9. Tests

`tests/test_beta.py` covers immutable rounds, scoring, duplicate callbacks, shared Daily sets, streak/rank, shared Friend Challenge sets, completion after two players, callback secrecy and schema/API baseline.

## 10. Known beta issues

- Real MAX acceptance still needs a valid bot token and a two-user manual run.
- Webhook HTTPS ingress and subscription setup are not included in local beta.
- Challenge notifications are shown when the player returns; no aggressive push scheduler is enabled.
- Existing old SQLite databases require a controlled backup and migration/reset because this is a closed-beta schema cutover.

## 11. Manual checklist

1. Set `BOT_TOKEN`, run migrations and load `content/beta_seed.json`.
2. User A sends `/start`, opens Daily, answers five questions and checks streak/rank.
3. User A creates `/challenge`, forwards the code/deep link and answers the round.
4. User B joins with `/join CODE`, answers the same questions and checks both results.
5. Press the callback twice, restart the bot, then verify no duplicate score and persistent Daily/Challenge state.

## 12. Next five improvements

1. Execute the real two-account MAX smoke and fix only observed SDK/event-shape gaps.
2. Add a small result-share helper using the documented MAX share deep link.
3. Add a controlled webhook runner and HTTPS deployment checklist.
4. Add richer challenge result names and explicit winner/draw achievements.
5. Add a content review command and a second licensed seed pack.
