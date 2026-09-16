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

set -e
# Parse command-line inputs for SLURM repo URL and name.
print_usage() {
    echo "Usage: $0 -u|--url <SLURM_REPO_URL> -n|--name <SLURM_REPO_NAME>"
    echo "       or: $0 <SLURM_REPO_URL> <SLURM_REPO_NAME>"
}

SLURM_REPO_URL=""
SLURM_REPO_NAME=""
LDMS_VERSION="4.5.1"
# Parse command-line option for LDMS version
while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--version)
            LDMS_VERSION="$2"
            shift 2
            ;;
        -u|--url)
            SLURM_REPO_URL="$2"
            shift 2
            ;;
        -n|--name)
            SLURM_REPO_NAME="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            # accept positional args if flags not used
            if [[ -z "$SLURM_REPO_URL" ]]; then
                SLURM_REPO_URL="$1"
            elif [[ -z "$SLURM_REPO_NAME" ]]; then
                SLURM_REPO_NAME="$1"
            elif [[ -z "$LDMS_VERSION" ]]; then
                LDMS_VERSION="$1"
            else
                echo "Unexpected argument: $1"
                print_usage
                exit 1
            fi
            shift
            ;;
    esac
done
echo "Using LDMS_VERSION=$LDMS_VERSION"
if [[ -z "$SLURM_REPO_URL" || -z "$SLURM_REPO_NAME" ]]; then
    echo "Warning: SLURM_REPO_URL and SLURM_REPO_NAME are not provided, user might not be able to generate ldms slurm metrics."
fi

echo "Using SLURM_REPO_URL=$SLURM_REPO_URL"
echo "Using SLURM_REPO_NAME=$SLURM_REPO_NAME"

# Get the script directory (handles monorepo src/rpm_build/ layout)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Target build scripts directory
TARGET_DIR="$SCRIPT_DIR/ldms"

# Print the result
echo "Target directory: $TARGET_DIR"

# === Step 1: Clone OVIS repo if not already present ===
REPO_URL="https://github.com/ovis-hpc/ovis.git"
DEST_DIR="$HOME/ovis-code"

mkdir -p "$DEST_DIR"
cd "$DEST_DIR"

if [ ! -d "ovis" ]; then
    echo "Cloning OVIS repository (version $LDMS_VERSION)..."
    git clone --branch v"$LDMS_VERSION" --depth 1 "$REPO_URL"
else
    echo "Repository already exists at $DEST_DIR/ovis. Skipping clone."
fi

# === Step 2: Export LDMS_REPO path ===
export LDMS_REPO="$DEST_DIR/ovis"
echo "LDMS_REPO set to $LDMS_REPO"

# === Step 3: Start container build script ===
# Verify target directory exists
if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory $TARGET_DIR does not exist."
    exit 1
fi

echo "Starting container build..."
if [[ -n "$SLURM_REPO_URL" && -n "$SLURM_REPO_NAME" ]]; then
    echo "Starting container build with SLURM_REPO_URL=$SLURM_REPO_URL and SLURM_REPO_NAME=$SLURM_REPO_NAME"
    bash "$TARGET_DIR/start_build_container.rockylinux10.bash" "$SLURM_REPO_URL" "$SLURM_REPO_NAME"
else
    echo "Warning: Starting container build without SLURM"
    bash "$TARGET_DIR/start_build_container.rockylinux10.bash"
fi
