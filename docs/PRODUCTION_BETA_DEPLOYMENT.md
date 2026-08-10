# Production beta: Cloud.ru VM, Managed PostgreSQL, MAX and Telegram

This repository contains a production image, fail-closed configuration gate and deployment scripts. A public launch is allowed only after every live gate in `LIVE_SMOKE_REPORT.md` is recorded as PASS. The current local checks do not create a Cloud.ru resource or change either bot.

## Topology

```text
MAX bot ──────── HTTPS /webhooks/max ────────┐
Telegram bot ── HTTPS /telegram/webhook ─────┼─ Caddy on Cloud.ru VM ─ FastAPI + Mini App
                                               │                              │
Players ─────── HTTPS / ──────────────────────┘                  private VPC ─┴─ Managed PostgreSQL
```

The VM is the only public component. PostgreSQL receives no public IP and its security group permits TCP 5432 only from the VM security group. Caddy obtains and renews the certificate after the public DNS A/AAAA record reaches the VM and inbound TCP 80/443 are open.

## One-time Cloud.ru setup

1. In the selected Cloud.ru project, create a VPC and a private subnet for the database. Create a second subnet or public interface for the VM.
2. Create a Managed PostgreSQL 16 Single instance in the private subnet, create database `quiz_battle` and a dedicated non-superuser application role. Store its password only in the VM runtime `.env`.
3. Create a Linux VM with a public IPv4 address, 2 vCPU, 4 GiB RAM and a 40 GiB SSD as the beta baseline. Attach it to the database VPC. Restrict SSH to the operator IP; allow 80/443 from the Internet.
4. Add the deployment public key to `quizdeploy`, verify a new SSH session with that key, install Docker Engine, then run `sudo sh prepare-host.sh`. The script refuses to disable SSH passwords until that key is present.
5. Point a real production hostname at the public IP, wait for DNS propagation, and use the same hostname in every URL below. Do not use a temporary tunnel for webhooks or Mini Apps.

Cloud.ru documents the VM-plus-private-PostgreSQL pattern, including the network boundary, in its [VM and PostgreSQL tutorial](https://cloud.ru/docs/tutorials-evolution/list/topics/free-tier-vm__postgresql-connection).

## Runtime configuration

On the VM create `/opt/quiz-battle/.env` with mode `0600` and owner `quizdeploy`. Start from `.env.example`, replace every example value, and keep these values aligned:

| Setting | Required production value |
| --- | --- |
| `ENV` / `BOT_MODE` | `production` / `webhook` |
| `DATABASE_URL` / `PG_DSN` | private `postgresql+asyncpg://` application URL and matching `postgresql://` backup-client URL |
| `MINI_APP_URL`, `WEBAPP_BASE_URL`, `API_BASE_URL`, `CORS_ORIGINS` | `https://<public-host>` |
| `MAX_WEBHOOK_URL` | `https://<public-host>/webhooks/max` |
| `TELEGRAM_WEBHOOK_URL` | `https://<public-host>/telegram/webhook` |
| `APP_SESSION_SECRET`, `MAX_WEBHOOK_SECRET`, `TELEGRAM_WEBHOOK_SECRET` | independent random values, never committed |

The production service executes `scripts.production_preflight` before migrations or startup. It rejects development mode, HTTP URLs, SQLite, absent secrets and example values.

## Deploy and rollback

GitVerse deployment pushes one immutable image reference, writes only `/opt/quiz-battle/.deploy.env`, applies migrations, bootstraps/audits content, then waits for `https://<public-host>/ready`. The runtime `.env` is never sent by CI and remains solely on the VM.

To roll back, set `IMAGE_REF` in `.deploy.env` to a previously accepted image digest or tag and run `/opt/quiz-battle/deploy.sh`. Do not roll back across a destructive database migration. Take and restore backups only with a separate PostgreSQL DSN using the `postgresql://` scheme, for example:

```sh
pg_dump --format=custom --no-owner --file /opt/quiz-battle/backups/quiz-battle-$(date +%F).dump "$PG_DSN"
pg_restore --clean --if-exists --no-owner --dbname "$RESTORE_DSN" /path/to/accepted-backup.dump
```

Run the restore command first against a new isolated database, then record its result in the live smoke report. Never use `--clean` against the live database.

## Bot and Mini App activation

After `/ready` and the public certificate both pass:

1. Run `python -m scripts.register_webhooks --dry-run` on the VM. It validates the complete local configuration without calling either platform.
2. Run `python -m scripts.register_webhooks --platform telegram`. It sets the Telegram HTTPS webhook and Menu Button Web App URL. Telegram signs webhook requests with the configured secret-token header.
3. In BotFather, set the same Mini App URL and confirm the displayed domain. The Bot API webhook and menu methods are defined in Telegram's [official Bot API](https://core.telegram.org/bots/api).
4. Run `python -m scripts.register_webhooks --platform max`. It subscribes `message_created`, `message_callback` and `bot_started` at the MAX HTTPS endpoint with the independent webhook secret.
5. In MAX Partner Cabinet, register the exact HTTPS Mini App domain and start a two-user device smoke. MAX requires a trusted HTTPS endpoint for production subscriptions; its subscription contract is documented at [POST /subscriptions](https://dev.max.ru/docs-api/methods/POST/subscriptions).

If either registration fails, keep the text fallback active, inspect only status codes and non-secret application logs, fix the configuration and retry. Do not switch a production bot to polling.
