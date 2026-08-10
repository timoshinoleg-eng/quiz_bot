# Cloud.ru Evolution deployment

This is the reproducible Cloud.ru production-beta path. It uses one public VM with Caddy and the application image, one private Managed PostgreSQL instance and one container registry repository. Kubernetes and a public database are intentionally excluded.

## Provisioning boundary

Create resources only after the Cloud.ru console shows the selected project, quota, supported services, grant coverage, current balance and price for the chosen region. Create a private VPC subnet for PostgreSQL, attach the VM to that network, and allow port 5432 only from the VM security group. The public VM permits 80/443 from the Internet and SSH only from the operator network.

Create one registry repository named `quiz-battle`; tag every image with the immutable Git SHA. Create an Object Storage bucket with private access for encrypted logical dumps and retain 14 days. The VM keeps the most recent local dump before a migration; a scheduled, credentialed upload to that bucket may be enabled only after the bucket and least-privilege access key exist.

Cloud.ru's supported VM/private-PostgreSQL topology is described in the [official tutorial](https://cloud.ru/docs/tutorials-evolution/list/topics/free-tier-vm__postgresql-connection). The current account has not been authenticated by this task, so no resource, billing assertion or bucket is claimed as created.

## Host installation

1. Create `quizdeploy` with its dedicated public key and verify SSH using that key.
2. Install Docker Engine and copy `deploy/vm/prepare-host.sh` to the VM.
3. Run it with `sudo`. It refuses to harden SSH without `quizdeploy`'s `authorized_keys` and grants that user Docker access.
4. Copy `deploy/compose.production.yml`, `deploy/Caddyfile` and `deploy/vm/deploy.sh` into `/opt/quiz-battle/`.
5. Create `/opt/quiz-battle/.env`, mode `0600`, owned by `quizdeploy`; populate it from `.env.example` with real values only on the VM.

`DATABASE_URL` is the SQLAlchemy `postgresql+asyncpg://` URL. `PG_DSN` is the same private connection using the standard `postgresql://` scheme and is used solely by `pg_dump`. Both values remain in the protected VM file.

## Release behavior

The VM deployment script pulls the requested immutable image, takes a compressed PostgreSQL dump, runs preflight/migration/content audit, starts the new application and waits for `/ready`. If readiness fails and a previous image exists, it restarts that previous application image. Migrations must remain backward-compatible with the preceding application version; the script does not perform destructive schema rollback.

For detailed platform activation, use [PRODUCTION_BETA_DEPLOYMENT.md](PRODUCTION_BETA_DEPLOYMENT.md). For day-two operations, use [PRODUCTION_RUNBOOK.md](PRODUCTION_RUNBOOK.md).
