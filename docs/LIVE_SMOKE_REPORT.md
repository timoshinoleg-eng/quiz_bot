# Live production-beta smoke report

Date: 2026-08-10. This report distinguishes local evidence from unperformed external actions; no platform or cloud success is inferred from source code.

| Gate | Status | Evidence / next proof |
| --- | --- | --- |
| Approved Grade 4 content + visual plan | PASS (local) | 500 active RU records in 5 subject packs x 100; answer-preserving metadata sync applied 74 first-wave visual, 32 reserve and 73 text-only decisions; audit: exact 0, fuzzy 0, invalid 0, missing provenance 0. Image assets remain a separate delivery. |
| Backend regression | PASS (local) | `pytest -q`: 23 passed after content and production preflight coverage |
| Mini App | PASS (local) | clean `npm ci`, typecheck, Vitest and production build pass |
| Production container | PASS (local runtime) | `quiz-battle:local` built, then isolated container returned `/health = ok` and `/ready = ready` |
| GitVerse private repository / CI run | BLOCKED | no confirmed authenticated GitVerse session or API credential; repository and workflow run do not yet exist |
| Cloud.ru VM / PostgreSQL / DNS / HTTPS | BLOCKED | no confirmed authenticated Cloud.ru session, project grant, VM, database or DNS record |
| Telegram webhook / Menu Web App | NOT RUN | requires deployed HTTPS endpoint and the dedicated Telegram bot token |
| MAX subscription / Partner Cabinet Mini App | NOT RUN | requires deployed HTTPS endpoint, correct Quiz Battle MAX token and cabinet access |
| Two-user cross-platform game | NOT RUN | perform only after both webhooks and signed init-data routes pass |
| Backup restore rehearsal | NOT RUN | restore an encrypted backup into an isolated PostgreSQL database |

Release verdict: **NO-GO for an external beta today.** The local product and deployment artefacts are ready for the external sequence, but GitVerse, Cloud.ru, DNS/HTTPS, MAX Partner Cabinet, BotFather and live two-user gates have not been evidenced. The exact external acceptance checklist is in `PRODUCTION_BETA_DEPLOYMENT.md`.
