#!/usr/bin/env sh
set -eu

APP_DIR=/opt/quiz-battle
COMPOSE_FILE="$APP_DIR/compose.production.yml"
RUNTIME_ENV="$APP_DIR/.env"
DEPLOY_ENV="$APP_DIR/.deploy.env"
BACKUP_DIR="$APP_DIR/backups"

test -f "$RUNTIME_ENV" || { echo "missing runtime .env" >&2; exit 1; }
test -f "$DEPLOY_ENV" || { echo "missing deployment image reference" >&2; exit 1; }

set -a
. "$DEPLOY_ENV"
. "$RUNTIME_ENV"
set +a

install -d -m 0700 "$BACKUP_DIR"
postgres_container=$(docker compose --env-file "$DEPLOY_ENV" -f "$COMPOSE_FILE" ps -q postgres 2>/dev/null || true)
if test -n "$postgres_container" && docker inspect --format '{{.State.Running}}' "$postgres_container" 2>/dev/null | grep -q true; then
    backup_file="$BACKUP_DIR/quiz-battle-$(date -u +%Y%m%dT%H%M%SZ).dump"
    docker compose --env-file "$DEPLOY_ENV" -f "$COMPOSE_FILE" exec -T postgres \
        pg_dump --format=custom --no-owner --username "$POSTGRES_USER" "$POSTGRES_DB" > "$backup_file"
fi
find "$BACKUP_DIR" -type f -name 'quiz-battle-*.dump' -mtime +14 -delete

previous_container=$(docker compose --env-file "$DEPLOY_ENV" -f "$COMPOSE_FILE" ps -q app 2>/dev/null || true)
previous_image=""
if test -n "$previous_container"; then
    previous_image=$(docker inspect --format '{{.Config.Image}}' "$previous_container" 2>/dev/null || true)
fi

docker compose --env-file "$DEPLOY_ENV" -f "$COMPOSE_FILE" pull
docker compose --env-file "$DEPLOY_ENV" -f "$COMPOSE_FILE" run --rm migrate
docker compose --env-file "$DEPLOY_ENV" -f "$COMPOSE_FILE" up -d --remove-orphans postgres app caddy

attempt=0
until curl --fail --silent --show-error --max-time 10 "https://$PUBLIC_HOST/ready" >/dev/null; do
    attempt=$((attempt + 1))
    if test "$attempt" -ge 12; then
        if test -n "$previous_image" && test "$previous_image" != "$IMAGE_REF"; then
            rollback_env=$(mktemp)
            printf 'IMAGE_REF=%s\nPUBLIC_HOST=%s\nACME_EMAIL=%s\n' "$previous_image" "$PUBLIC_HOST" "$ACME_EMAIL" > "$rollback_env"
            docker compose --env-file "$rollback_env" -f "$COMPOSE_FILE" up -d --no-deps app caddy
            rm -f "$rollback_env"
            echo "post-deploy readiness failed; restored previous application image" >&2
        fi
        exit 1
    fi
    sleep 5
done

echo "deployment completed"
