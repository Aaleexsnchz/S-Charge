#!/usr/bin/env bash
#
# Weekly automated backup (invoked from cron).
#
#   1. Writes a PII-safe seed dump to backups/ (timestamped local history).
#   2. Uploads it to Backblaze B2 (bucket S-Charge, server-side encrypted
#      at rest) via rclone — the offsite copy. No user/oauth data leaves the box.
#   3. Prunes local and offsite seed dumps beyond the most recent $KEEP.
#
# See scripts/backup_db.sh for the manual/full-dump variant and the restore
# command. Cron has a minimal PATH and does not load the shell profile, so both
# the PATH and the rclone config are set here rather than inherited.
#
# Paths are derived from $HOME instead of being written out: they were hardcoded
# to the development laptop's home, which on any other host resolves to nothing
# and — this being cron — would have failed into an empty log nobody reads.
# Every override below can be set in the environment for an unusual host.
#
# **COMPOSE_FILE must be set to docker-compose.prod.yml on the server**, or the
# dump addresses a dev project that has never run there. Until 2026-08-23 this
# script had never run on the server at all — rclone was not installed and no
# cron entry existed — so the offsite copy described above did not exist. Verify
# a real upload lands rather than trusting that it does.
#
set -euo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:${HOME}/.local/bin"

cd "$(dirname "$0")/.."

KEEP="${KEEP:-8}"
RCLONE="${RCLONE:-rclone}"
export RCLONE_CONFIG="${RCLONE_CONFIG:-${HOME}/.config/rclone/rclone.conf}"
REMOTE="${REMOTE:-b2:S-Charge}"

# Fail loudly and before dumping anything. An unconfigured host must not look
# like a successful backup.
command -v "$RCLONE" >/dev/null 2>&1 || {
    echo "backup aborted: rclone not found (looked on PATH=$PATH)" >&2
    exit 1
}
[ -r "$RCLONE_CONFIG" ] || {
    echo "backup aborted: no readable rclone config at $RCLONE_CONFIG" >&2
    exit 1
}

./scripts/backup_db.sh --seed
dump="$(ls -t backups/ev_charging_seed_*.dump | head -1)"

"$RCLONE" copy "$dump" "$REMOTE/"

# Prune local: keep the newest $KEEP.
ls -t backups/ev_charging_seed_*.dump | tail -n +$((KEEP + 1)) | xargs -r rm -f

# Prune offsite: keep the newest $KEEP (ISO-timestamped names sort chronologically).
"$RCLONE" lsf "$REMOTE" | grep '^ev_charging_seed_.*\.dump$' | sort | head -n "-$KEEP" |
    while read -r f; do
        "$RCLONE" deletefile --b2-hard-delete "$REMOTE/$f"
    done

printf 'backup complete: %s -> %s\n' "$dump" "$REMOTE"
