#!/bin/bash
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Script to check if GitLab HTTPS port is being used by non-GitLab processes
# Usage: check_gitlab_port.sh <port_number>
# Exit codes: 0 = healthy GitLab, free port, or GitLab-owned port; 1 = conflict

set -euo pipefail

# Port number to check
PORT="${1:-443}"

if curl -fsS "http://127.0.0.1:${PORT}/-/health" >/dev/null; then
  echo "[OK] GitLab healthy on ${PORT}"
  exit 0
fi

# Capture output first so grep -q cannot SIGPIPE a pipeline under pipefail.
listeners="$(ss -ltn "sport = :${PORT}" 2>/dev/null || true)"
if ! grep -q LISTEN <<<"${listeners}"; then
  echo "[INFO] Port ${PORT} free; starting GitLab…"
  # Note: In Ansible context, we don't actually start GitLab here
  exit 0
fi

# Check if owner appears to be GitLab (Omnibus paths/users)
owners="$(lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null || true)"
if grep -Eq '/opt/gitlab|/var/opt/gitlab|gitlab-www|gitlab-workhorse|puma' <<<"${owners}"; then
  echo "[OK] Port ${PORT} is owned by GitLab components; continuing."
  exit 0
fi

echo "[ERROR] Port ${PORT} is occupied by a non-GitLab process:"
ss -ltnp "sport = :${PORT}" || true
exit 1
