#!/bin/bash
# sync_catalog.sh
# Fetches catalog from a remote endpoint and commits/pushes to GitLab.
#
# Usage:
#   ./sync_catalog.sh
# Environment variables (can also edit defaults below):
#   REMOTE_CATALOG_URL   - URL to download catalog from (HTTP/S, S3 presigned, etc.)
#   REPO_DIR             - Local clone of the GitLab project
#   BRANCH               - Branch to commit to (default main)
#   CATALOG_AUTH_HEADER  - Optional "Authorization: Bearer ..." header

set -euo pipefail

REMOTE_CATALOG_URL="${REMOTE_CATALOG_URL:-https://api.example.com/catalog/latest}"
REPO_DIR="${REPO_DIR:-/opt/gitlab-repos/omnia-catalog}"
BRANCH="${BRANCH:-main}"
CATALOG_FILE="catalog.yml"
AUTH_HEADER="${CATALOG_AUTH_HEADER:-}"

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO  $*"; }
warn() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARN  $*"; }
die()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR $*"; exit 1; }

log "Starting catalog sync"
log "Remote URL: $REMOTE_CATALOG_URL"
log "Repo dir:   $REPO_DIR"
log "Branch:     $BRANCH"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  die "Git repository not found at $REPO_DIR"
fi

cd "$REPO_DIR"

git fetch origin "$BRANCH"
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

log "Downloading catalog"
CURL_OPTS=(-fsSL --max-time 30)
[[ -n "$AUTH_HEADER" ]] && CURL_OPTS+=(-H "$AUTH_HEADER")

curl "${CURL_OPTS[@]}" "$REMOTE_CATALOG_URL" -o "${CATALOG_FILE}.tmp"

log "Comparing with current $CATALOG_FILE"
if cmp -s "$CATALOG_FILE" "${CATALOG_FILE}.tmp"; then
  rm -f "${CATALOG_FILE}.tmp"
  log "No changes detected; exiting"
  exit 0
fi

mv "${CATALOG_FILE}.tmp" "$CATALOG_FILE"

git add "$CATALOG_FILE"
COMMIT_MSG="Sync catalog from remote source\n\nSource: $REMOTE_CATALOG_URL\nTimestamp: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"

git commit -m "$COMMIT_MSG"
log "Pushing to origin/$BRANCH"
git push origin "$BRANCH"

log "Done. GitLab should trigger a pipeline now."
