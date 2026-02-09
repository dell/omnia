#!/bin/bash
# trigger_pipeline.sh
# Triggers a GitLab pipeline via the API and passes optional variables.
#
# Usage: ./trigger_pipeline.sh [JOBID]
# Required env vars:
#   GITLAB_URL            - e.g. http://100.10.0.83
#   GITLAB_PROJECT_ID     - numeric project ID
#   GITLAB_TRIGGER_TOKEN  - pipeline trigger token created in GitLab UI
# Optional env vars:
#   GITLAB_REF            - branch (default main)

set -euo pipefail

GITLAB_URL="${GITLAB_URL:-http://100.10.0.83}"
PROJECT_ID="${GITLAB_PROJECT_ID:-1}"
TRIGGER_TOKEN="${GITLAB_TRIGGER_TOKEN:-}"  # must be provided
REF="${GITLAB_REF:-main}"
JOBID="${1:-$(date +%s)}"

if [[ -z "$TRIGGER_TOKEN" ]]; then
  echo "ERROR: GITLAB_TRIGGER_TOKEN not set"
  exit 1
fi

echo "Triggering pipeline on $GITLAB_URL (project $PROJECT_ID, ref $REF, JOBID $JOBID)"

RESPONSE=$(curl -sS -X POST \
  "$GITLAB_URL/api/v4/projects/${PROJECT_ID}/trigger/pipeline" \
  -F token="$TRIGGER_TOKEN" \
  -F ref="$REF" \
  -F variables[JOBID]="$JOBID")

PIPELINE_ID=$(echo "$RESPONSE" | python -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null || true)
PIPELINE_URL=$(echo "$RESPONSE" | python -c "import sys,json;print(json.load(sys.stdin).get('web_url',''))" 2>/dev/null || true)

if [[ -n "$PIPELINE_ID" ]]; then
  echo "Pipeline triggered successfully: ID $PIPELINE_ID"
  [[ -n "$PIPELINE_URL" ]] && echo "View at: $PIPELINE_URL"
else
  echo "Failed to trigger pipeline. Response: $RESPONSE"
  exit 1
fi
