# Quiz Battle MAX V2 implementation report

> Historical implementation snapshot. The former content-duplicate blocker was remediated locally; use [LIVE_SMOKE_REPORT.md](LIVE_SMOKE_REPORT.md) for the current release gates.

## Delivered local implementation

The baseline MAX text bot now has a Vite + React Mini App, a FastAPI game API,
10 catalog packs, server-authoritative rounds, Daily, challenge codes, basic
profile/leaderboard endpoints and a MAX text fallback. The production identity
path accepts only validated MAX `initData`; browser identity is restricted to
`ENV=development`.

The follow-up acceptance repair also fixed the V2 runtime path: a Quick game
created with the legacy `general` category now draws from active catalog
questions, and Daily creates its required seven-question round. The frontend
uses the live profile, achievements, leaderboard, timer and answer-feedback
endpoints rather than static figures.

## Verified locally on 2026-08-10

- `pytest -q`: 19 passed.
- `python -m compileall -q .`: passed.
- `frontend`: `npm run build` passed.
- A clean SQLite database completed migrations, content bootstrap and API smoke:
  10 packs, 550 active Russian questions, Quick = 5 and Daily = 7.
- Server responses used by the player do not expose `correct_answer` or
  `wrong_answers`.

## Content status — release blocker

The corpus has 550 active Russian records and no exact duplicate texts,
invalid options, placeholder distractors or missing explanations. It still has
**218 near-duplicate question variants**. The audit now fails on that result,
so the CI gate cannot falsely accept the corpus. Replacing those variants with
editorially distinct, sourced questions is required before a public beta.

## Still outside the delivered scope

- Live Partner Cabinet registration, HTTPS deployment, MAX signed-initData and
  two-user smoke have not been evidenced.
- External-provider import adapters, automatic translation with review, and
  media questions are not implemented.
- Daily theme rotation, weekly missions, combo mechanics, a full achievement
  taxonomy and challenge-completion notification are not implemented.
- Docker Desktop was unavailable during local acceptance, therefore
  `docker compose build` was not verified.

See [V2_ACCEPTANCE_AUDIT.md](V2_ACCEPTANCE_AUDIT.md) for the requirement-by-requirement verdict.
