#!/bin/bash

# Script to check if GitLab HTTPS port is being used by non-GitLab processes
# Usage: check_gitlab_port.sh <port_number>

# Port number to check
PORT=${1:-443}

# Main logic using the exact provided approach
( curl -fsS "http://127.0.0.1:${PORT}/-/health" >/dev/null && echo "[OK] GitLab healthy on ${PORT}" && exit 0 ) \
|| if ! ss -ltn "sport = :${PORT}" | grep -q LISTEN; then
     echo "[INFO] Port ${PORT} free; starting GitLab…"
     # Note: In Ansible context, we don't actually start GitLab here
     exit 0
   else
     # Check if owner appears to be GitLab (Omnibus paths/users)
     if lsof -nP -iTCP:${PORT} -sTCP:LISTEN 2>/dev/null | grep -E '/opt/gitlab|/var/opt/gitlab|gitlab-www|gitlab-workhorse|puma' >/dev/null; then
       echo "[OK] Port ${PORT} is owned by GitLab components; continuing."
       exit 0
     else
       echo "[ERROR] Port ${PORT} is occupied by a non-GitLab process:"
       ss -ltnp "sport = :${PORT}"
       exit 1
     fi
   fi
