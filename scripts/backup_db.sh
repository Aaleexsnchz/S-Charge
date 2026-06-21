#!/usr/bin/env bash
#
# Logical backup of the Postgres DB. The seed costs ~12 days under REVE's
# 5 req/hr cap, so these dumps are both the disaster-recovery copy and the
# production-bootstrap artifact.
#
#   ./scripts/backup_db.sh          full dump (schema + all data) — disaster recovery
#   ./scripts/backup_db.sh --seed   excludes users/oauth_account rows — safe to publish
#
# Restore into a fresh, empty database with:
#   docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
#     --clean --if-exists --no-owner < backups/<file>.dump
#
set -euo pipefail

cd "$(dirname "$0")/.."

: "${POSTGRES_USER:=ev_charging_app}"
: "${POSTGRES_DB:=ev_charging}"

mode="${1:-full}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out_dir="backups"
mkdir -p "$out_dir"

case "$mode" in
full)
    out_file="${out_dir}/ev_charging_${stamp}.dump"
    dump_args=()
    ;;
--seed | seed)
    out_file="${out_dir}/ev_charging_seed_${stamp}.dump"
    dump_args=(--exclude-table-data=users --exclude-table-data=oauth_account)
    ;;
*)
    echo "usage: $0 [full|--seed]" >&2
    exit 2
    ;;
esac

docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc "${dump_args[@]}" >"$out_file"
printf 'Wrote %s (%s)\n' "$out_file" "$(du -h "$out_file" | cut -f1)"
