#!/usr/bin/env bash
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

# =============================================================================
# Build the omnia-auto wheel
# =============================================================================
# Usage:
#   ./build_wheel.sh              Build the wheel
#   ./build_wheel.sh --install    Build and install into current venv
#   ./build_wheel.sh --clean      Clean build artifacts only
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

INSTALL=false
CLEAN_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --install) INSTALL=true ;;
        --clean) CLEAN_ONLY=true ;;
        --help|-h)
            echo "Usage: $0 [--install] [--clean]"
            echo "  --install   Build and install into current venv"
            echo "  --clean     Clean build artifacts only"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}"
            exit 1
            ;;
    esac
done

# --- Clean ---
echo -e "${YELLOW}Cleaning build artifacts...${NC}"
rm -rf dist/ build/ omnia_auto.egg-info/

if [ "$CLEAN_ONLY" = true ]; then
    echo -e "${GREEN}Clean complete.${NC}"
    exit 0
fi

# --- Check build tool ---
if ! python3 -m build --version &>/dev/null; then
    echo -e "${YELLOW}Installing build tool...${NC}"
    pip install build
fi

# --- Build ---
echo -e "${YELLOW}Building wheel...${NC}"
python3 -m build --wheel 2>&1

WHEEL=$(ls dist/*.whl 2>/dev/null | head -1)
if [ -z "$WHEEL" ]; then
    echo -e "${RED}Build failed — no wheel found in dist/${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Wheel built: ${WHEEL}${NC}"

# --- Install ---
if [ "$INSTALL" = true ]; then
    echo -e "${YELLOW}Installing wheel...${NC}"
    pip install --force-reinstall "$WHEEL"
    echo -e "${GREEN}Installed: $(pip show omnia-auto 2>/dev/null | grep Version)${NC}"
fi

echo -e "${GREEN}Done.${NC}"
