# Quiz Battle MAX V2 — acceptance audit

Reviewed locally on 2026-08-10 against the supplied V2 brief. A green unit
suite is not a production acceptance: live MAX and deployment checks are
reported separately.

| Area | Verdict | Evidence / gap |
| --- | --- | --- |
| Mini App, responsive game UI and MAX text fallback | PARTIAL | React build passes; Home, catalog, game, feedback, result and bottom navigation are implemented. No live MAX visual or device smoke was available. |
| Catalog of 10 packs | PASS | Clean bootstrap produced 10 non-empty packs, 55 active questions each. |
| 500+ active Russian questions | PARTIAL | 550 active RU records exist, but 218 near-duplicate variants remain. This is a public-beta blocker. |
| Correct answers and answer validation | PASS | Authoritative database check and API smoke confirm the player response does not include answer keys. Duplicate callbacks remain idempotent. |
| Quick Game and question selection | PASS | Regression covers a no-`general` catalog: Quick returns five active questions. The user may select 5/10/15/20. |
| Daily Challenge | PASS | Regression/API smoke confirms exactly seven questions, one daily game policy, streak and leaderboard service paths. |
| Profile, XP, levels, basic achievements and leaderboard | PASS | API endpoints return persisted profile/progress/achievement and leaderboard data; UI reads them live. |
| Friend challenge and sharing | PARTIAL | Challenge code/deep-link API and sharing fallbacks exist; there is no live two-account completion, notification or rematch smoke. |
| Timer, feedback and result screen | PASS | Client has a countdown, timeout answer, feedback lock and result view; frontend production build passes. |
| Daily themes, weekly missions, combo and expanded achievements | FAIL | Not implemented in the current product. |
| External providers, translation review and media questions | FAIL | Not implemented. The content source file only records research status. |
| Content audit and CI | PARTIAL | Audit reports packs/categories/difficulty/sources and blocks exact/near duplicates. CI runs it plus frontend tests/build, but no remote Actions run has been evidenced. |
| Production security | PARTIAL | Production requires `APP_SESSION_SECRET` and validated MAX init data. HTTPS, Partner Cabinet registration, production database/backup restore and rate-limit evidence are absent. |
| Docker build | UNKNOWN | Docker Desktop daemon was stopped locally; `docker compose build` could not run. |
| Required documentation | PARTIAL | Architecture/content/deployment documentation exists, but it must be updated when the missing provider, translation and release paths are implemented. |

## Fixed during this review

1. The active V2 catalog no longer leaves Quick/Daily empty when it receives the
   legacy `general` category.
2. Daily now accepts and creates its seven-question game instead of being
   rejected by the round-size validator.
3. The frontend now uses live profile, achievement and leaderboard data, has a
   working timer/timeout, and preserves answer totals between questions.
4. The production session signer now fails closed without `APP_SESSION_SECRET`.
5. The audit and CI now detect near-duplicate content rather than treating a
   cosmetic rewording as a successful corpus.

## Release verdict

**NO-GO for public beta.** The shortest path to a private pilot is: replace the
218 near-duplicate variants with distinct sourced questions; run the clean
database/audit gate successfully; then complete HTTPS, Partner Cabinet,
signed-initData and two-account MAX smoke. Until those gates pass, retain the
text-bot fallback and do not market the Mini App as production ready.
