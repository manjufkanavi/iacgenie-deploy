#!/bin/bash
# sync-gitea-mirrors.sh
# Pull mirrors for all Gitea-hosted repos to sync from GitHub.
# Run on the Gitea host (mkanavi@192.168.0.118) inside the mkanavi user shell.
# NOTE: MUST be run with clean environment — no TMPDIR from macOS or other shells.

set -euo pipefail

# Force clean environment to avoid TMPDIR=/var/folders/... inheritance
export TMPDIR=/tmp
export HOME=/home/mkanavi
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

REPOS="iacgenie LightSerp iacgenie-unified-infra"

for repo in $REPOS; do
    cd /home/mkanavi/git/gitea-repos/$repo.git || continue
    echo "=== Syncing $repo ==="
    # Force-gate: only run if the last Gitea push was >5 min ago
    if [ -f .git/refs/heads/main ]; then
        LAST_GITEA=$(stat -c %Y .git/refs/heads/main 2>/dev/null || echo 0)
        NOW=$(date +%s)
        if [ $((NOW - LAST_GITEA)) -lt 300 ]; then
            echo "  Skipped — last Gitea push within 5 min"
            continue
        fi
    fi
    # Ensure mirror remote exists, then pull
    git remote add github git@github.com:manjufkanavi/${repo}.git 2>/dev/null || true
    git fetch github --quiet 2>&1 | tail -1 || echo "  Fetch failed (check SSH key)"
    if git branch --list -r github/main | grep -q main; then
        git reset --hard github/main
        echo "  Pulled github/main"
    else
        echo "  No main branch on GitHub, skipping reset"
    fi
done

echo "=== Done ==="
