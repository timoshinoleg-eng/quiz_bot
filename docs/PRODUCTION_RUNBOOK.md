# Production runbook

## Health and logs

On the VM, run `curl --fail https://$PUBLIC_HOST/health` and `curl --fail https://$PUBLIC_HOST/ready`. Inspect the application with `docker compose --env-file .deploy.env -f compose.production.yml logs --tail=200 app` and Caddy with the same command ending in `caddy`. Do not paste `.env`, init-data or Authorization headers into tickets.

## Restart and rollback

Restart the application with `docker compose --env-file .deploy.env -f compose.production.yml up -d app caddy`, then require `/ready`. To roll back a bad image, write the previously accepted immutable image value to `.deploy.env` together with the unchanged public-host values, run `./deploy.sh`, then record the result. Do not roll back an incompatible database migration.

## Backup and restore

Every deployment writes a custom PostgreSQL dump to `/opt/quiz-battle/backups` before migration and removes files older than 14 days. Copy encrypted dumps to the private Object Storage bucket only after its least-privilege credential has been configured. Test recovery exclusively against a newly created isolated database:

```sh
pg_restore --list /opt/quiz-battle/backups/accepted.dump
pg_restore --clean --if-exists --no-owner --dbname "$RESTORE_DSN" /opt/quiz-battle/backups/accepted.dump
```

Never run `pg_restore --clean` against the production DSN.

## Webhooks

After HTTPS and `/ready` pass, run `python -m scripts.register_webhooks --dry-run`, then run each platform command separately. Telegram registration sets both `setWebhook` and `setChatMenuButton`; MAX registration creates its subscription. Verify Telegram with `getWebhookInfo`, verify MAX through a real callback, and record only non-secret status evidence.
