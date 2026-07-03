#!/bin/bash

CERT_PATH="/opt/omnia/pulp/settings/certs/pulp_webserver.crt"
ANCHOR_PATH="/etc/pki/ca-trust/source/anchors"
LOG_DIR="/opt/omnia/log/core"
LOG_FILE="${LOG_DIR}/pulp_cert_log"

mkdir -p "$LOG_DIR"
: > "$LOG_FILE"

echo "$(date '+%Y-%m-%d %H:%M:%S'): Container started" >> "$LOG_FILE"

if [ -f "$CERT_PATH" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S'): Cert found at $CERT_PATH" >> "$LOG_FILE"

  cp -f "$CERT_PATH" "$ANCHOR_PATH/"
  echo "$(date '+%Y-%m-%d %H:%M:%S'): Copied cert to $ANCHOR_PATH" >> "$LOG_FILE"

  update-ca-trust extract
  echo "$(date '+%Y-%m-%d %H:%M:%S'): Ran update-ca-trust" >> "$LOG_FILE"
else
  echo "$(date '+%Y-%m-%d %H:%M:%S'): Cert not found at $CERT_PATH" >> "$LOG_FILE"
fi

exec "$@"
