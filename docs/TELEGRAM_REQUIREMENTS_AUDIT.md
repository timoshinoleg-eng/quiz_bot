# Telegram requirements audit — Phase A

Audit target: committed `HEAD` `2b5da48ee8aace1cfde6a90bb536de7e3b72c5a4`, compared with pre-Telegram base `165b387`. The source working tree was dirty before the audit; its uncommitted changes are not evidence for this committed target.

Status meanings: **PASS** is locally evidenced, **PARTIAL** is only partly implemented, **FAIL** is locally disproved, and **NOT VERIFIABLE** needs real Telegram/HTTPS credentials.

| ID | Original requirement | Status | Evidence | Problem |
|---|---|---|---|---|
| T01 | One product, no Telegram game clone | PASS | `db.py`, `api.py`, no Telegram scoring/selector service | Shared core is reused. |
| T02 | Platform identity with unique platform/external ID | PASS | `models.py`, migration 003, identity test | MAX/TG `123` stay distinct. |
| T03 | Clean migration and one Alembic head | PASS | fresh SQLite `upgrade head`, `current`, `heads` | Historical 002 relies on current metadata, but upgrade completed. |
| T04 | Thin Telegram bot with seven commands | PARTIAL | `telegram_bot.py` handlers exist | No bot handler/integration tests and no graceful session lifecycle. |
| T05 | Main Mini App, profile/menu/startapp | NOT VERIFIABLE | Buttons and setup guide exist | BotFather/HTTPS/Menu Button are not configured locally. |
| T06 | Shared Mini App Home/Catalog/Game/Result/Daily/Profile/Leaderboard | PARTIAL | `frontend/src/main.tsx` screens exist | Screens are minimal; Daily has no dedicated presentation and leaderboard/profile UX is incomplete. |
| T07 | Browser mock, no production impersonation | PARTIAL | `VITE_PLATFORM=mock`, `X-Development-User` only under development | No browser-flow test; mock has no explicit selectable mock user. |
| T08 | Telegram initData security | PARTIAL | HMAC procedure is correct; 2 broad tests | Missing separate username/hash/missing/malformed/replay tests and endpoint test. |
| T09 | Origin security | PARTIAL | configurable CORS origins | Development localhost default and no production-origin validation test. |
| T10 | Telegram theme/safe area | FAIL | frontend has no CSS/theme bridge consumption | No theme variables, safe-area or screenshot coverage. |
| T11 | Fullscreen/haptic feature detection | PARTIAL | optional methods are called | No tap/selection handling or tests; real client behavior is unverified. |
| T12 | Same catalog, 10 packs, >=500 RU active | PARTIAL | clean bootstrap: 550/10 | 90 exact +164 fuzzy duplicates in the source bank. |
| T13 | Quality Russian content, no placeholders | PARTIAL | 100-question stratified sample; no placeholder/invalid rows | Sample had 12 exact and 14 fuzzy duplicates; explanation text is generic. |
| T14 | Licensed/provider provenance | PARTIAL | `CONTENT_SOURCES.md` says project CC0 | No external factual citations/independent source attribution for 550 facts. |
| T15 | Quick Game: immediate 5-question round | FAIL | clean localhost smoke: POST games `422` | V2 content has no `general` category, while the committed selector requires it. |
| T16 | Unseen → wrong → long-ago selector | PARTIAL | sorting logic in `_question_pool` | No acceptance test, and Quick pool is broken on clean V2 content. |
| T17 | Game screen: title/progress/timer/score/feedback | PARTIAL | React game screen | No pack title/category or combo; feedback skips directly to next question. |
| T18 | No answer leakage / server score / duplicate answer | PARTIAL | `public_game`, `answer_game`, small unit test | No endpoint-level recursive leakage or malicious request suite. |
| T19 | Daily: 7 questions, one/day, streak | FAIL | clean localhost `GET /daily` returned `500` | Same broken `general` selector; no date-boundary/streak matrix. |
| T20 | Cross-platform shared Daily | FAIL | no cross-platform Daily test | Cannot start Daily in clean committed state. |
| T21 | Friend challenge immutable pair and abuse resistance | PARTIAL | shared persistence methods exist | No committed test; no winner/draw model/API and no rematch API/UI. |
| T22 | Telegram share and opaque startapp challenge link | PARTIAL | frontend makes `t.me/<user>?startapp=challenge_<code>` | No prepared-message API, no fallback when username absent, no deep-link test; live unverified. |
| T23 | Challenge result/winner/rematch | FAIL | no winner/draw calculation or rematch route/UI | Original social loop is incomplete. |
| T24 | XP/levels | PARTIAL | `_award_progress` uses fixed XP/level formula | No math/idempotency test beyond incomplete game suite; no Daily/challenge bonuses. |
| T25 | Pack mastery | PARTIAL | `/me/progress` aggregates by category | Formula is unique-seen count mislabeled as `seen`; UI did not render it in committed HEAD. |
| T26 | Achievements | FAIL | only `first_game`, `perfect`, `streak_3`, `streak_7` | Missing required broader achievement set and UI behavior. |
| T27 | Three weekly missions | FAIL | no mission model/service/API/UI | Required P1 feature absent. |
| T28 | Weekly leaderboard with player/neighbours | PARTIAL | backend top list exists | No current-user rank, neighbours or points-to-next; frontend only placeholder. |
| T29 | Analytics events | PARTIAL | only `app_open`, `challenge_create`, `challenge_join` persisted | Most requested events absent; failure isolation untested. |
| T30 | Privacy/no secret leakage | PARTIAL | no unnecessary PII fields; tracked files contain no real token | initData/token logging and webhook paths lack tests. |
| T31 | Notifications/write-access restraint | PASS | no automatic Daily notifications or permission prompt | Challenge notification itself is not implemented. |
| T32 | Group Battle beta prototype | PARTIAL | explicitly deferred | Original permits a minimal prototype/defer only after personal flow; not a V1 DoD item. |
| T33 | Poll fallback/media/home-screen/rich/ephemeral | PARTIAL | none implemented or documented as adopted/rejected | Optional/deferred items were not investigated in code/docs. |
| T34 | MAX local regression | PARTIAL | MAX HMAC and shared-core smoke tests exist | Only 5 committed tests total; no clean MAX runtime/daily/challenge acceptance. |
| T35 | CI: backend, content, frontend, Docker | PARTIAL | workflow declares jobs | HEAD has no frontend tests/typecheck script; local Docker daemon unavailable. |
| T36 | Clean install reproducibility | PARTIAL | fresh venv/migration/bootstrap succeeds | Content audit exits success despite duplicate threshold; Quick/Daily fail. |
| T37 | Setup documentation | PARTIAL | `TELEGRAM_SETUP.md` includes BotFather/HTTPS/webhook/deep link | Does not give executable webhook registration/check path or distinguish direct Main App link mechanics precisely. |
| T38 | README and implementation report factual claims | FAIL | source inspection and localhost smoke | They imply a usable common Daily/Quick path despite clean committed state failure. |

## Phase A outcome

- **Fully PASS:** T01–T03, T31 (4).
- **PARTIAL:** T04, T06–T09, T11–T14, T16–T18, T21–T22, T24–T25, T28–T30, T32–T37 (25).
- **FAIL:** T10, T15, T19–T20, T23, T26–T27, T38 (9).
- **NOT VERIFIABLE WITHOUT LIVE CONFIG:** T05 plus real Telegram theme, haptics, fullscreen, share, startapp, two-account challenge and webhook reception.

Critical requirements: PASS 3, PARTIAL 8, FAIL 4. Non-critical deferred: Group Battle, polls, media, homescreen, rich/ephemeral UX.

## Previous claims that were inaccurate / overstated

1. “12 passed” was not reproducible from Git: exact clean `HEAD` collected **5** tests. Seven prior tests were ignored/untracked.
2. “Quick Game: WORKING” and “Daily: WORKING” were false for the clean committed V2 corpus: localhost returned `422` and `500` respectively.
3. “Telegram V1 implemented” overstated feature coverage: missions, full achievements, winner/draw/rematch, theme/safe-area support and most analytics did not exist.
4. “Content 550” was numerically true but not quality-accepted: 90 exact and 164 fuzzy duplicates remained, and the audit command did not fail on them.
