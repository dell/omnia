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

set -euo pipefail

# Fixed path: s3cmd reads ~/.s3cfg and the container runs as root. Not taken
# from the environment, so the secret key cannot be redirected elsewhere.
readonly S3CFG_FILE="/root/.s3cfg"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-}"
MINIO_HOST="${MINIO_HOST:-localhost:9000}"
MINIO_USE_HTTPS="${MINIO_USE_HTTPS:-False}"
# When HTTPS is used, verify the MinIO certificate and host name unless the
# operator explicitly opts out. MINIO_CA_CERTS_FILE trusts a private CA.
MINIO_VERIFY_TLS="${MINIO_VERIFY_TLS:-True}"
MINIO_CA_CERTS_FILE="${MINIO_CA_CERTS_FILE:-}"

if [ -z "$MINIO_ACCESS_KEY" ] || [ -z "$MINIO_SECRET_KEY" ]; then
    echo "WARNING: MINIO_ACCESS_KEY or MINIO_SECRET_KEY not set. s3cmd will not work without valid credentials."
    echo "Please set both environment variables or mount a valid .s3cfg file."
    exit 0
fi

for flag in MINIO_USE_HTTPS MINIO_VERIFY_TLS; do
    case "${!flag}" in
        True|False) ;;
        *) echo "ERROR: $flag must be True or False." >&2; exit 1 ;;
    esac
done

# These values are written into the config file, so reject line breaks.
for var in MINIO_ACCESS_KEY MINIO_SECRET_KEY MINIO_HOST MINIO_CA_CERTS_FILE; do
    if [[ "${!var}" == *$'\n'* || "${!var}" == *$'\r'* ]]; then
        echo "ERROR: $var must not contain line breaks." >&2
        exit 1
    fi
done

if [ -n "$MINIO_CA_CERTS_FILE" ] && [ ! -r "$MINIO_CA_CERTS_FILE" ]; then
    echo "ERROR: MINIO_CA_CERTS_FILE is not readable: $MINIO_CA_CERTS_FILE" >&2
    exit 1
fi

if [ "$MINIO_USE_HTTPS" = "True" ] && [ "$MINIO_VERIFY_TLS" = "False" ]; then
    echo "WARNING: MinIO TLS certificate verification is disabled (MINIO_VERIFY_TLS=False)." >&2
fi

if [ -L "$S3CFG_FILE" ]; then
    echo "ERROR: $S3CFG_FILE is a symlink; refusing to write credentials through it." >&2
    exit 1
fi

# Create the file owner-only from the start; it holds the S3 secret key.
umask 077
cat > "$S3CFG_FILE" <<EOF
[default]
access_key = ${MINIO_ACCESS_KEY}
secret_key = ${MINIO_SECRET_KEY}
host_base = ${MINIO_HOST}
host_bucket = ${MINIO_HOST}
use_https = ${MINIO_USE_HTTPS}
signature_v2 = False
check_ssl_certificate = ${MINIO_VERIFY_TLS}
check_ssl_hostname = ${MINIO_VERIFY_TLS}
ca_certs_file = ${MINIO_CA_CERTS_FILE}
EOF

chmod 600 "$S3CFG_FILE"
echo "s3cmd configuration initialized at $S3CFG_FILE"
