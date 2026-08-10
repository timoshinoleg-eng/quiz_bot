# Quiz Battle production-beta checklist

## Local acceptance

- [x] `python -m compileall -q .`
- [x] `pytest -q`
- [x] `python -m scripts.content.bootstrap` and `python -m scripts.content.audit`
- [x] `npm run typecheck`, `npm test` and `npm run build` in `frontend`
- [x] production image build plus isolated `/health` and `/ready` response
- [x] Caddy and production Compose configuration validation
- [x] webhook registration dry-run for MAX and Telegram

## External acceptance

- [ ] Private GitVerse repository has the committed source, CI/CD enabled and a green exact-main run.
- [ ] Cloud.ru VM, private Managed PostgreSQL, DNS and public HTTPS certificate are live.
- [ ] Runtime `.env` passes `python -m scripts.production_preflight` on the VM.
- [ ] PostgreSQL backup restore was rehearsed against an isolated database.
- [ ] BotFather has the exact HTTPS Mini App URL; Telegram webhook and menu button are registered.
- [ ] MAX Partner Cabinet has the exact HTTPS Mini App URL; MAX subscription is registered.
- [ ] Two distinct users complete Daily, Quick Game and Friend Challenge in each platform.

The commands, environment contract and rollback path are in `docs/PRODUCTION_BETA_DEPLOYMENT.md`. Do not mark the beta public until every external item has a recorded PASS.
