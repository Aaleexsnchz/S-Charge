#!/usr/bin/env bash
#
# Weekly automated backup (invoked from cron).
#
#   1. Writes a PII-safe seed dump to backups/ (timestamped local history).
#   2. Uploads it to Backblaze B2 (bucket tfm-db-backups, server-side encrypted
#      at rest) via rclone — the offsite copy. No user/oauth data leaves the box.
#   3. Prunes local and offsite seed dumps beyond the most recent $KEEP.
#
# See scripts/backup_db.sh for the manual/full-dump variant and the restore
# command. Cron has a minimal PATH and does not load the shell profile, so the
# rclone binary and config are referenced by absolute path.
#
set -euo pipefail
export PATH="/usr/bin:/bin"

cd "$(dirname "$0")/.."

KEEP=8
RCLONE=/home/aaleexsnchz/.local/bin/rclone
export RCLONE_CONFIG=/home/aaleexsnchz/.config/rclone/rclone.conf
REMOTE="b2:tfm-db-backups"

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
