# Quiz Battle MAX V2 — acceptance audit

Reviewed locally on 2026-08-10 against the supplied V2 brief. A green unit
suite is not a production acceptance: live MAX and deployment checks are
reported separately.

| Area | Verdict | Evidence / gap |
| --- | --- | --- |
| Mini App, responsive game UI and MAX text fallback | PARTIAL | React build passes; Home, catalog, game, feedback, result and bottom navigation are implemented. No live MAX visual or device smoke was available. |
| Catalog of 5 subject packs | PASS | Replacement bootstrap produced five non-empty fourth-grade subject packs, 100 active questions each. |
| 500 active Russian questions | PASS (local) | Replacement bootstrap produces 500 active RU records for ages 10–11. Audit reports exact 0, fuzzy 0, invalid 0 and missing provenance 0. |
| Correct answers and answer validation | PASS | Authoritative database check and API smoke confirm the player response does not include answer keys. Duplicate callbacks remain idempotent. |
| Quick Game and question selection | PASS | Regression covers a no-`general` catalog: Quick returns five active questions. The user may select 5/10/15/20. |
| Daily Challenge | PASS | Regression/API smoke confirms exactly seven questions, one daily game policy, streak and leaderboard service paths. |
| Profile, XP, levels, basic achievements and leaderboard | PASS | API endpoints return persisted profile/progress/achievement and leaderboard data; UI reads them live. |
| Friend challenge and sharing | PARTIAL | Challenge code/deep-link API and sharing fallbacks exist; there is no live two-account completion, notification or rematch smoke. |
| Timer, feedback and result screen | PASS | Client has a countdown, timeout answer, feedback lock and result view; frontend production build passes. |
| Daily themes, weekly missions, combo and expanded achievements | FAIL | Not implemented in the current product. |
| External providers, translation review and media questions | FAIL | Not implemented. The content source file only records research status. |
| Content audit and CI | PARTIAL | Local audit reports packs/categories/difficulty/sources and blocks exact/near duplicates plus missing provenance. GitVerse workflows are committed, but no remote Actions run has been evidenced. |
| Production security | PARTIAL | Production requires `APP_SESSION_SECRET` and validated MAX init data. HTTPS, Partner Cabinet registration, production database/backup restore and rate-limit evidence are absent. |
| Docker build | PASS (local) | Production image builds and an isolated container returns both `/health = ok` and `/ready = ready`. |
| Required documentation | PARTIAL | Architecture/content/deployment documentation exists, but it must be updated when the missing provider, translation and release paths are implemented. |

## Fixed during this review

1. The active V2 catalog no longer leaves Quick/Daily empty when it receives the
   legacy `general` category.
2. Daily now accepts and creates its seven-question game instead of being
   rejected by the round-size validator.
3. The frontend now uses live profile, achievement and leaderboard data, has a
   working timer/timeout, and preserves answer totals between questions.
4. The production session signer now fails closed without `APP_SESSION_SECRET`.
5. The former catalogue was replaced with 500 distinct fourth-grade questions;
   bootstrap/audit now passes on the active corpus.
6. Production preflight, Caddy HTTPS proxy, registry-to-VM deployment scripts
   and GitVerse workflows were added and validated locally.

## Release verdict

**NO-GO for an external beta.** The content and container gates now pass
locally. The remaining sequence is external and must be evidenced: private
GitVerse CI, Cloud.ru VM/Managed PostgreSQL/DNS/HTTPS, MAX Partner Cabinet,
BotFather, signed init-data and two-account MAX/Telegram smoke. Until those
gates pass, retain the text-bot fallback and do not market the Mini App as
production ready.
