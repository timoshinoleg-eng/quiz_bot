# Telegram final acceptance

Date: 2026-08-10. This is an independent acceptance of the committed Telegram target and the current local remediation worktree; it is not a production or live-Telegram claim.

## 1. Git state

```text
Branch: main
HEAD: 2b5da48ee8aace1cfde6a90bb536de7e3b72c5a4
Ahead/behind origin/main: 4/0
Telegram commits: 2ca13e3, 2b5da48
Dirty: YES — tracked and untracked implementation, content, frontend, docs and test changes exist.
```

The accepted clean `HEAD` was checked in `C:\tmp\quiz-bot-telegram-audit-2b5da48`; the dirty worktree is not equivalent to that commit and must not be called released.

## 2. Original requirements

```text
PASS: 8
PARTIAL: 22
FAIL: 7
NOT VERIFIABLE: 1 category (multiple live checks)
```

Detailed traceability is in [TELEGRAM_REQUIREMENTS_AUDIT.md](TELEGRAM_REQUIREMENTS_AUDIT.md). Locally corrected since Phase A: `general` Quick/Daily selection, seven-question Daily validation, test tracking, frontend typecheck/Vitest and theme/safe-area variables. The following remain failed: unique editor-reviewed corpus, mission system, expanded achievements, winner/draw/rematch flow, and complete leaderboard UX.

## 3. Backend

Current dirty-tree localhost smoke against a newly migrated/bootstrapped SQLite DB returned `/health` 200, `/api/v1/quizzes` with 10 packs, `/api/v1/daily` 200 and a five-question Quick Game 200. Game payloads did not contain exact `correct_answer` or `correct_index` keys; a repeated answer was idempotent.

## 4. Telegram Bot

`telegram_bot.py` implements command routing for `/start`, `/play`, `/daily`, `/challenge`, `/profile`, `/leaderboard` and `/help` and delegates gameplay to shared HTTP/core paths. Polling and a secret-header webhook adapter exist. No real bot token or Telegram update was used.

## 5. Mini App

Home, catalog, game, result, profile and leaderboard React states exist. Current working code has timer/feedback, profile/mastery and leaderboard reads. It remains a compact single-file UI; no real Telegram client visual acceptance occurred.

## 6. Auth/security

Telegram HMAC validation matches the official WebAppData procedure: signed raw `initData`, sorted data-check string, token-derived HMAC, constant-time compare and one-hour age bound. Local tests reject modified user data, malformed/missing/duplicate hash, invalid hash and stale data. `PlatformIdentity` has `platform + external_user_id` uniqueness and keeps same-number MAX/Telegram identities distinct.

## 7. Content

```text
Active RU: 550
Quiz packs: 10 (55 active records each)
Exact duplicates: 0 in current worktree audit
Fuzzy duplicates: 218 (blocking)
Sample reviewed: 100, stratified 10 per pack; 0 exact, 4 fuzzy within sample
Content defect rate: at least 4% sampled near-duplicate, 39.6% corpus near-duplicate pairs/records reported by audit
```

The sample facts were age-appropriate and generally factual, but generic explanations and corpus near-duplicates make the content requirement **not accepted**. `python -m scripts.content.audit` correctly exits non-zero now.

## 8. Game

Immutable game questions, server-side score and duplicate-answer idempotency have regression tests. Current local Quick Game starts immediately with five questions. Pack title/category and combo UX are incomplete.

## 9. Daily

Current local API and regression tests show a common seven-question daily set and one-game policy. Date rollover, missed-day reset and cross-platform identities on the same Daily are not sufficiently tested.

## 10. Challenge

Shared immutable challenge create/join persistence exists. There is no accepted winner/draw calculation, rematch endpoint/UI, full abuse suite or Telegram two-account acceptance.

## 11. Progression

Base XP, levels, streak, category-derived mastery and four persisted achievements exist. Weekly missions are absent; achievement and leaderboard requirements are only partially implemented.

## 12. Telegram-specific

The current bridge has feature-detected BackButton, haptic, fullscreen, theme and safe-area support; pure deep-link helpers have Vitest coverage. Prepared messages, write access, native polls, media questions, homescreen, rich/ephemeral UX and Group Battle are not implemented. Group Battle is deferred and not a V1 DoD blocker, but must not be advertised.

## 13. MAX regression

Imports, signed MAX initData unit coverage, shared game/Daily/challenge tests and frontend build pass locally. Live MAX bot, Mini App, Partner Cabinet and two-user regression are **NOT VERIFIABLE LOCALLY**.

## 14. Tests

```text
Collected: 19
Passed: 19
Failed: 0
Skipped: 0
Auth/platform identity: 7
Game/Daily/Challenge/shared MAX: 10
API/content/runtime: 2
```

This is still materially below the requested acceptance coverage for Daily calendar boundaries, challenge abuse/winner/rematch, progression, endpoint auth and full Telegram transport.

## 15. Frontend

```text
typecheck: PASS (`tsc -b --noEmit`)
tests: PASS (Vitest, 2 assertions)
build: PASS
```

## 16. Docker

**NOT RUN / NOT PASS.** Docker Desktop's Linux engine pipe was unavailable, so neither image build nor image smoke was performed.

## 17. CI

```text
Local equivalent: PARTIAL PASS — Python, frontend and API checks run; content audit intentionally fails; Docker unavailable.
Remote: NOT RUN — no publication or Actions run was authorized.
```

## 18. Clean-install reproducibility

A fresh worktree/venv install, Alembic upgrade and content bootstrap recreated 550 records and 10 packs. On clean committed `HEAD`, however, Quick/Daily failed and the content audit reported 90 exact/164 fuzzy duplicates. Current remedies are still dirty, so no clean-checkout acceptance exists for the remediated version.

## 19. Live checks still required

1. BotFather Main Mini App and Menu Button with production HTTPS origin.
2. Real Telegram signed-initData login, theme, haptic, fullscreen and webhook reception.
3. Two-account Telegram challenge/share/rematch acceptance.
4. Real MAX two-user Mini App/Daily/challenge regression.
5. Docker build/image smoke after Docker Desktop starts.

## 20. Final verdict

**NO-GO.** Local Quick/Daily regressions were repaired in the dirty worktree, but a public beta cannot pass while the content gate reports 218 fuzzy duplicates, required missions/expanded progression and challenge outcome/rematch are absent, tests remain narrow, and the remediated state has not been committed or clean-bootstrapped.
