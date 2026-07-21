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

# =============================================================================
# build_images.sh — BuildStream Container Build (Self-Contained)
# =============================================================================
# Builds the omnia_build_stream container (FastAPI build automation + S3).
#
# Usage:
#   ./build_images.sh                                        # Build (default)
#   ./build_images.sh build_stream_tag=1.2                   # Custom tag
#   ./build_images.sh build_tool=docker                      # Use docker
#   ./build_images.sh build_tool=docker build_action=push    # Push to registry
#   ./build_images.sh registry=myregistry.io/myrepo          # Custom registry
#
# Parameters:
#   build_stream_tag=<tag>     Image tag (default: 1.1)
#   build_tool=<tool>          podman | docker (default: podman)
#   build_action=<action>      load | push (default: load)
#   registry=<url>             Registry URL (default: docker.io/dellhpcomniaaisolution)
# =============================================================================

set -euo pipefail

# ── Resolve paths ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Color codes ──
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# =============================================================================
# Show help
# =============================================================================
show_help() {
    echo -e "${GREEN}BuildStream Container Build Script${NC}"
    echo -e "${GREEN}======================================${NC}"
    echo ""
    echo -e "${BLUE}USAGE:${NC}"
    echo "  ./build_images.sh [parameters]"
    echo ""
    echo -e "${BLUE}PARAMETERS (key=value format):${NC}"
    echo "  build_stream_tag=<tag>     Image tag (default: 1.1)"
    echo "  build_tool=<tool>          podman | docker (default: podman)"
    echo "  build_action=<action>      load | push (default: load)"
    echo "  registry=<url>             Registry URL (default: docker.io/dellhpcomniaaisolution)"
    echo ""
    echo -e "${BLUE}EXAMPLES:${NC}"
    echo "  ./build_images.sh"
    echo "  ./build_images.sh build_stream_tag=1.2"
    echo "  ./build_images.sh build_tool=docker"
    echo "  ./build_images.sh build_tool=docker build_action=push"
    echo "  ./build_images.sh registry=myregistry.io/myrepo"
    echo ""
    echo -e "${BLUE}NOTES:${NC}"
    echo "  - build_action=push requires build_tool=docker"
    echo "  - Default registry: docker.io/dellhpcomniaaisolution"
    echo "  - Builds the omnia_build_stream container (FastAPI + S3)"
    exit 0
}

# =============================================================================
# Default parameterized values
# =============================================================================
BUILD_TOOL="podman"
BUILD_ACTION="load"
OMNIA_DOCKER_REGISTERY="docker.io/dellhpcomniaaisolution"
BUILD_STREAM_TAG="1.1"

# =============================================================================
# Parse command-line parameters (key=value format)
# =============================================================================
for arg in "$@"; do
    case "$arg" in
        build_tool=*)          BUILD_TOOL="${arg#*=}" ;;
        build_action=*)        BUILD_ACTION="${arg#*=}" ;;
        registry=*)            OMNIA_DOCKER_REGISTERY="${arg#*=}" ;;
        build_stream_tag=*)    BUILD_STREAM_TAG="${arg#*=}" ;;
        -h|--help)
            show_help
            ;;
        *)
            echo -e "${RED}Error: Unknown parameter '$arg'${NC}"
            echo -e "${YELLOW}Valid: build_stream_tag, build_tool, build_action, registry${NC}"
            exit 1
            ;;
    esac
done

# =============================================================================
# Validate inputs
# =============================================================================
if [[ "$BUILD_TOOL" != "podman" && "$BUILD_TOOL" != "docker" ]]; then
    echo -e "${RED}Error: Invalid build_tool '${BUILD_TOOL}'. Valid: podman, docker${NC}"
    exit 1
fi

if [[ "$BUILD_ACTION" != "load" && "$BUILD_ACTION" != "push" ]]; then
    echo -e "${RED}Error: Invalid build_action '${BUILD_ACTION}'. Valid: load, push${NC}"
    exit 1
fi

if [[ "$BUILD_ACTION" == "push" && "$BUILD_TOOL" != "docker" ]]; then
    echo -e "${RED}Error: build_action=push requires build_tool=docker${NC}"
    exit 1
fi

# =============================================================================
# Build omnia_build_stream container
# =============================================================================
echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN} BuildStream — Container Build         ${NC}"
echo -e "${GREEN}=======================================${NC}"
echo -e "${BLUE}Build tool:   ${BUILD_TOOL}${NC}"
echo -e "${BLUE}Build action: ${BUILD_ACTION}${NC}"
echo -e "${BLUE}Tag:          ${BUILD_STREAM_TAG}${NC}"
echo ""

BUILD_DIR="${SCRIPT_DIR}/omnia_build_stream"

cd "$BUILD_DIR" || exit 1

BUILD_RESULT=0

if [ "$BUILD_TOOL" = "podman" ]; then
    podman build -t "omnia_build_stream:${BUILD_STREAM_TAG}" -f "Containerfile" .
    BUILD_RESULT=$?
elif [ "$BUILD_TOOL" = "docker" ]; then
    if [ "$BUILD_ACTION" = "load" ]; then
        docker buildx build --no-cache -t "omnia_build_stream:${BUILD_STREAM_TAG}" \
            --file "Containerfile" --platform "linux/amd64" --network=host --load .
        BUILD_RESULT=$?
    elif [ "$BUILD_ACTION" = "push" ]; then
        docker buildx build --no-cache \
            -t "${OMNIA_DOCKER_REGISTERY}/omnia_build_stream:${BUILD_STREAM_TAG}" \
            --file "Containerfile" --platform "linux/amd64" --network=host \
            --provenance=true --sbom=true --push .
        BUILD_RESULT=$?
    fi
fi

cd - > /dev/null || exit 1

if [ $BUILD_RESULT -eq 0 ]; then
    echo -e "\n${GREEN}omnia_build_stream:${BUILD_STREAM_TAG} built successfully.${NC}"
    if [ "$BUILD_TOOL" = "docker" ] && [ "$BUILD_ACTION" = "push" ]; then
        echo -e "${GREEN}Pushed: ${OMNIA_DOCKER_REGISTERY}/omnia_build_stream:${BUILD_STREAM_TAG}${NC}"
    fi
else
    echo -e "\n${RED}omnia_build_stream:${BUILD_STREAM_TAG} build FAILED.${NC}"
    exit 1
fi
