#!/usr/bin/env bash
#
# Logical backup of the Postgres DB. The seed costs ~12 days under REVE's
# 5 req/hr cap, so these dumps are both the disaster-recovery copy and the
# production-bootstrap artifact.
#
#   ./scripts/backup_db.sh          full dump (schema + all data) — disaster recovery
#   ./scripts/backup_db.sh --seed   excludes users/oauth_account rows — safe to publish
#
# COMPOSE_FILE selects the stack, and defaults to the dev one. **On the server it
# must be set to docker-compose.prod.yml** — the two files declare different
# project names, so an unqualified `docker compose` there addresses a dev project
# that has never run and the dump fails with "service db is not running". That is
# how the weekly offsite backup silently did nothing, into a log nobody reads.
#
# Restore into a fresh, empty database with:
#   docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
#     --clean --if-exists --no-owner < backups/<file>.dump
#
set -euo pipefail

cd "$(dirname "$0")/.."

: "${COMPOSE_FILE:=docker-compose.yml}"
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

# Fail before dumping, and name the likely cause. Addressing the wrong stack
# looks identical to a broken database, and this one went unnoticed for weeks
# because the only place it said so was a cron log.
docker compose -f "$COMPOSE_FILE" ps --status running --services 2>/dev/null |
    grep -qx db || {
    rm -f "$out_file"
    echo "backup aborted: no running db service in $COMPOSE_FILE" >&2
    echo "  on the server, set COMPOSE_FILE=docker-compose.prod.yml" >&2
    exit 1
}

# The shell creates the file before pg_dump runs, so any failure leaves a
# plausible-looking artifact behind rather than nothing. That is how a 0-byte
# dump reached the offsite bucket on 2026-07-13. `|| status=$?` rather than
# letting `set -e` abort, so the check below runs on the failing path too and
# the bad file is removed instead of lingering for the next `ls -t` to find.
status=0
docker compose -f "$COMPOSE_FILE" exec -T db \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
    "${dump_args[@]}" >"$out_file" || status=$?

# Even a schema-only archive clears 4 KiB, so anything smaller is a failure that
# exited 0 — the case a status check alone would miss.
MIN_BYTES=4096
size="$(wc -c <"$out_file")"
if [ "$status" -ne 0 ] || [ "$size" -lt "$MIN_BYTES" ]; then
    rm -f "$out_file"
    echo "backup failed: pg_dump exited ${status}, wrote ${size} bytes" >&2
    exit 1
fi

# Size only proves the file is not empty. A dump truncated by a full disk is
# large and unusable, and would upload happily and eventually prune a good copy
# out of the retention window.
#
# `pg_restore -f /dev/null` decodes every member and so reaches the end of the
# archive. `pg_restore -l` does not: the table of contents sits at the front, so
# a truncated dump lists cleanly — verified against a deliberately truncated
# archive, which -l accepted and this rejects. Still not a restore, which the
# automated check owed in Phase 13 would be.
if ! docker compose -f "$COMPOSE_FILE" exec -T db pg_restore -f /dev/null \
    <"$out_file" >/dev/null 2>&1; then
    # Kept, not deleted, unlike the checks above: those fire on a file that is
    # provably worthless, while a misfire here would bin a good backup and leave
    # nothing to examine. `.suspect` does not match the retention glob, so it is
    # invisible to pruning and to the uploader.
    mv "$out_file" "$out_file.suspect"
    echo "backup failed: ${size} bytes written but the archive did not decode" >&2
    echo "  kept as ${out_file}.suspect for inspection" >&2
    exit 1
fi

printf 'Wrote %s (%s)\n' "$out_file" "$(du -h "$out_file" | cut -f1)"
