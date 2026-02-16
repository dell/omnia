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

# Generate RSA key pair for JWT signing
#
# This script generates a 4096-bit RSA key pair for signing JWT tokens.
# The keys are stored in the specified directory with appropriate permissions.
#
# Usage:
#   ./generate_jwt_keys.sh [output_directory]
#
# Default output directory: /etc/omnia/keys

set -euo pipefail

# Configuration
KEY_SIZE=4096
PRIVATE_KEY_NAME="jwt_private.pem"
PUBLIC_KEY_NAME="jwt_public.pem"
DEFAULT_OUTPUT_DIR="/opt/omnia/build_stream/api/.auth/keys"

# Parse arguments
OUTPUT_DIR="${1:-$DEFAULT_OUTPUT_DIR}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if openssl is available
if ! command -v openssl &> /dev/null; then
    log_error "openssl is required but not installed."
    exit 1
fi

# Create output directory if it doesn't exist
if [ ! -d "$OUTPUT_DIR" ]; then
    log_info "Creating output directory: $OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
fi

PRIVATE_KEY_PATH="$OUTPUT_DIR/$PRIVATE_KEY_NAME"
PUBLIC_KEY_PATH="$OUTPUT_DIR/$PUBLIC_KEY_NAME"

# Check if keys already exist
if [ -f "$PRIVATE_KEY_PATH" ] || [ -f "$PUBLIC_KEY_PATH" ]; then
    log_warn "JWT keys already exist in $OUTPUT_DIR"
    read -p "Do you want to overwrite them? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Key generation cancelled."
        exit 0
    fi
    log_warn "Overwriting existing keys..."
fi

log_info "Generating $KEY_SIZE-bit RSA private key..."
openssl genrsa -out "$PRIVATE_KEY_PATH" "$KEY_SIZE" 2>/dev/null

if [ $? -ne 0 ]; then
    log_error "Failed to generate private key"
    exit 1
fi

log_info "Extracting public key..."
openssl rsa -in "$PRIVATE_KEY_PATH" -pubout -out "$PUBLIC_KEY_PATH" 2>/dev/null

if [ $? -ne 0 ]; then
    log_error "Failed to extract public key"
    rm -f "$PRIVATE_KEY_PATH"
    exit 1
fi

# Set secure permissions
log_info "Setting secure permissions..."
chmod 600 "$PRIVATE_KEY_PATH"  # Owner read/write only
chmod 644 "$PUBLIC_KEY_PATH"   # Owner read/write, others read

# Verify the keys
log_info "Verifying key pair..."
VERIFY_RESULT=$(openssl rsa -in "$PRIVATE_KEY_PATH" -check 2>&1)
if echo "$VERIFY_RESULT" | grep -q "RSA key ok"; then
    log_info "Key verification successful"
else
    log_error "Key verification failed"
    exit 1
fi

# Display key information
log_info "JWT keys generated successfully!"
echo ""
echo "Key Details:"
echo "  Private Key: $PRIVATE_KEY_PATH"
echo "  Public Key:  $PUBLIC_KEY_PATH"
echo "  Key Size:    $KEY_SIZE bits"
echo "  Algorithm:   RS256 (RSA with SHA-256)"
echo ""
echo "Environment Variables (add to your configuration):"
echo "  export JWT_PRIVATE_KEY_PATH=\"$PRIVATE_KEY_PATH\""
echo "  export JWT_PUBLIC_KEY_PATH=\"$PUBLIC_KEY_PATH\""
echo ""
echo "Key Rotation Recommendations:"
echo "  - Rotate keys every 365 days for production environments"
echo "  - Keep backup of old public key for token validation during rotation"
echo "  - Update JWT_KEY_ID environment variable when rotating keys"
echo ""
log_warn "IMPORTANT: Keep the private key secure and never commit it to version control!"
