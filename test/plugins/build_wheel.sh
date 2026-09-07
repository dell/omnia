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
# Build and validate the omnia-auto distributions
# =============================================================================
# Usage:
#   ./build_wheel.sh              Build the wheel and source distribution
#   ./build_wheel.sh --install    Build, validate, and install into active venv
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
PYTHON_CMD="${OMNIA_AUTO_PYTHON:-python3}"

for arg in "$@"; do
    case "$arg" in
        --install) INSTALL=true ;;
        --clean) CLEAN_ONLY=true ;;
        --help|-h)
            echo "Usage: $0 [--install] [--clean]"
            echo "  --install   Build and install into the active virtual environment"
            echo "  --clean     Clean build artifacts only"
            echo ""
            echo "Set OMNIA_AUTO_PYTHON=/path/to/python to select the interpreter."
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}"
            exit 1
            ;;
    esac
done

if [ "$CLEAN_ONLY" = true ]; then
    echo -e "${YELLOW}Cleaning build artifacts...${NC}"
    rm -rf -- dist build omnia_auto.egg-info
    echo -e "${GREEN}Clean complete.${NC}"
    exit 0
fi

# --- Check build tools ---
if ! "$PYTHON_CMD" -m build --version &>/dev/null; then
    echo -e "${RED}Missing build dependency for ${PYTHON_CMD}.${NC}"
    echo "Install development tools first:"
    echo "  ${PYTHON_CMD} -m pip install --upgrade '.[dev]'"
    exit 1
fi

if ! "$PYTHON_CMD" -m twine --version &>/dev/null; then
    echo -e "${RED}Missing twine dependency for ${PYTHON_CMD}.${NC}"
    echo "Install development tools first:"
    echo "  ${PYTHON_CMD} -m pip install --upgrade '.[dev]'"
    exit 1
fi

# --- Clean ---
echo -e "${YELLOW}Cleaning build artifacts...${NC}"
rm -rf -- build omnia_auto.egg-info

ARTIFACT_TMP=$(mktemp -d)
trap 'rm -rf -- "$ARTIFACT_TMP"' EXIT

# --- Build ---
echo -e "${YELLOW}Building wheel and source distribution...${NC}"
"$PYTHON_CMD" -m build --outdir "$ARTIFACT_TMP" 2>&1

WHEELS=("$ARTIFACT_TMP"/*.whl)
SDISTS=("$ARTIFACT_TMP"/*.tar.gz)
if [ ! -e "${WHEELS[0]}" ] || [ ! -e "${SDISTS[0]}" ]; then
    echo -e "${RED}Build failed — wheel or source distribution missing.${NC}"
    exit 1
fi

echo -e "${YELLOW}Validating distribution metadata...${NC}"
"$PYTHON_CMD" -m twine check "$ARTIFACT_TMP"/*

rm -rf -- dist
mv "$ARTIFACT_TMP" dist
trap - EXIT
WHEELS=(dist/*.whl)
SDISTS=(dist/*.tar.gz)

echo ""
echo -e "${GREEN}Built: ${WHEELS[*]}${NC}"
echo -e "${GREEN}Built: ${SDISTS[*]}${NC}"

# --- Install ---
if [ "$INSTALL" = true ]; then
    IN_VENV=$("$PYTHON_CMD" -c 'import sys; print(int(sys.prefix != sys.base_prefix))')
    if [ "$IN_VENV" != "1" ]; then
        echo -e "${RED}--install requires an active virtual environment.${NC}"
        exit 1
    fi
    echo -e "${YELLOW}Installing wheel into the active virtual environment...${NC}"
    "$PYTHON_CMD" -m pip install --force-reinstall "${WHEELS[0]}"
    VERSION=$("$PYTHON_CMD" -m pip show omnia-auto 2>/dev/null | awk '/^Version:/ {print $2}')
    echo -e "${GREEN}Installed omnia-auto ${VERSION}.${NC}"
fi

echo -e "${GREEN}Done.${NC}"
