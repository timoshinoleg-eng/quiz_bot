# Quiz Battle MAX V2 implementation report

## Before

The real baseline was a MAX text bot with 30 seed questions and seven regression tests.

## Product changes

React Mini App now has a game-style Home, pack catalog, timed answer view, feedback, result/share view and bottom navigation. The bot retains the text fallback and links its «Играть» action to `MINI_APP_URL` when configured.

## Architecture

`frontend/` is Vite + React + TypeScript. `api.py` is FastAPI over the existing authoritative `db_manager`; it serves catalog, content stats, profile, game and answer endpoints. Production identity comes only from validated MAX `initData`; browser mock identity exists only under `ENV=development`.

## Content

Bootstrap installs **550 V2 RU records in 10 packs**; the legacy 30-record seed is retained but inactive. `python -m scripts.content.audit` is the acceptance gate.

## Known issues

Mini App Partner-Cabinet registration, HTTPS hosting and live MAX two-user smoke still require the owner. The current curated pack needs a second editorial pass to remove semantically repetitive variants before public rollout.
