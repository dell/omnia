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
# build_images.sh — OIM Core Container Build (Self-Contained)
# =============================================================================
# Builds the core OIM containers: omnia_core and omnia_auth.
#
# Usage:
#   ./build_images.sh                                        # Build core + auth (default)
#   ./build_images.sh core                                   # Core only
#   ./build_images.sh auth                                   # Auth only
#   ./build_images.sh core core_tag=2.3                      # Custom tag
#   ./build_images.sh core,auth build_tool=docker            # Use docker
#   ./build_images.sh all build_tool=docker build_action=push # Push to registry
#
# Available containers:
#   all, core, auth
#
# Other domain containers have their own build scripts:
#   Telemetry:      src/telemetry/containers/build_images.sh
#   BuildStream:    src/build_stream/containers/build_images.sh
#   Image Builder:  src/image_build_manager/containers/build_images.sh
#
# Parameters:
#   build_tool=<tool>          podman | docker (default: podman)
#   build_action=<action>      load | push (default: load)
#   registry=<url>             Registry URL (default: docker.io/dellhpcomniaaisolution)
#   core_tag=<tag>             omnia_core tag (default: 2.2)
#   auth_tag=<tag>             omnia_auth tag (default: 1.1)
# =============================================================================

set -euo pipefail

# ── Resolve paths ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# ── Color codes ──
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[34m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# ── Build status tracking ──
SUCCESSFUL_BUILDS=()
FAILED_BUILDS=()

# =============================================================================
# Show help
# =============================================================================
show_help() {
    echo -e "${GREEN}OIM Core Container Build Script${NC}"
    echo -e "${GREEN}======================================${NC}"
    echo ""
    echo -e "${BLUE}USAGE:${NC}"
    echo "  ./build_images.sh [container] [parameters]"
    echo ""
    echo -e "${BLUE}CONTAINERS:${NC}"
    echo "  all                    Build core + auth (default)"
    echo "  core                   Build omnia_core container"
    echo "  auth                   Build omnia_auth container"
    echo "  Multiple containers can be comma-separated: core,auth"
    echo ""
    echo -e "${BLUE}OTHER DOMAIN CONTAINERS:${NC}"
    echo "  Telemetry:      src/telemetry/containers/build_images.sh"
    echo "  BuildStream:    src/build_stream/containers/build_images.sh"
    echo "  Image Builder:  src/image_build_manager/containers/build_images.sh"
    echo ""
    echo -e "${BLUE}PARAMETERS (key=value format):${NC}"
    echo "  build_tool=<tool>          podman | docker (default: podman)"
    echo "  build_action=<action>      load | push (default: load)"
    echo "  registry=<url>             Registry URL (default: docker.io/dellhpcomniaaisolution)"
    echo "  core_tag=<tag>             omnia_core tag (default: 2.2)"
    echo "  auth_tag=<tag>             omnia_auth tag (default: 1.1)"
    echo ""
    echo -e "${BLUE}EXAMPLES:${NC}"
    echo "  ./build_images.sh"
    echo "  ./build_images.sh core"
    echo "  ./build_images.sh core core_tag=2.3"
    echo "  ./build_images.sh core,auth build_tool=docker"
    echo "  ./build_images.sh all build_tool=docker build_action=push"
    echo ""
    echo -e "${BLUE}NOTES:${NC}"
    echo "  - build_action=push requires build_tool=docker"
    echo "  - Default registry: docker.io/dellhpcomniaaisolution"
    echo "  - After build, run: ./omnia.sh --install"
    exit 0
}

# =============================================================================
# Default parameterized values
# =============================================================================
BUILD_TOOL="podman"
BUILD_ACTION="load"
OMNIA_DOCKER_REGISTERY="docker.io/dellhpcomniaaisolution"

CORE_TAG="2.2"
AUTH_TAG="1.1"

# =============================================================================
# Parse command-line parameters
# =============================================================================
CONTAINER_ARG="${1:-all}"
shift 2>/dev/null || true

for arg in "$@"; do
    case "$arg" in
        build_tool=*)      BUILD_TOOL="${arg#*=}" ;;
        build_action=*)    BUILD_ACTION="${arg#*=}" ;;
        registry=*)        OMNIA_DOCKER_REGISTERY="${arg#*=}" ;;
        core_tag=*)        CORE_TAG="${arg#*=}" ;;
        auth_tag=*)        AUTH_TAG="${arg#*=}" ;;
        -h|--help)
            show_help
            ;;
        *)
            echo -e "${RED}Error: Unknown parameter '$arg'${NC}"
            echo -e "${YELLOW}Valid: build_tool, build_action, registry, core_tag, auth_tag${NC}"
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
# Container build function (self-contained)
# =============================================================================
container_build() {
    local image_name="$1"
    local image_tag="$2"
    local build_dir="$3"
    local containerfile="$4"
    local extra_args="${5:-}"
    local platform="${6:-linux/amd64}"

    cd "$build_dir" || exit 1

    local BUILD_RESULT

    if [ "$BUILD_TOOL" = "podman" ]; then
        # shellcheck disable=SC2086
        podman build ${extra_args} -t "${image_name}:${image_tag}" -f "${containerfile}" .
        BUILD_RESULT=$?
    elif [ "$BUILD_TOOL" = "docker" ]; then
        if [ "$BUILD_ACTION" = "load" ]; then
            # shellcheck disable=SC2086
            docker buildx build --no-cache ${extra_args} -t "${image_name}:${image_tag}" \
                --file "${containerfile}" --platform "${platform}" --load .
            BUILD_RESULT=$?
        elif [ "$BUILD_ACTION" = "push" ]; then
            # shellcheck disable=SC2086
            docker buildx build --no-cache ${extra_args} \
                -t "${OMNIA_DOCKER_REGISTERY}/${image_name}:${image_tag}" \
                --file "${containerfile}" --platform "${platform}" \
                --provenance=true --sbom=true --push .
            BUILD_RESULT=$?
        fi
    fi

    cd - > /dev/null || exit 1

    if [ $BUILD_RESULT -eq 0 ]; then
        echo -e "${GREEN}${image_name}:${image_tag} built successfully.${NC}"
        SUCCESSFUL_BUILDS+=("${image_name}")
    else
        echo -e "${RED}${image_name}:${image_tag} build FAILED.${NC}"
        FAILED_BUILDS+=("${image_name}")
    fi
}

# =============================================================================
# Build functions
# =============================================================================
build_omnia_core() {
    echo -e "${BLUE}Building omnia_core (tag: ${CORE_TAG})...${NC}"
    container_build "omnia_core" "${CORE_TAG}" \
        "${REPO_ROOT}" "src/main/containers/omnia_core/Containerfile"
}

build_omnia_auth() {
    echo -e "${BLUE}Building omnia_auth (tag: ${AUTH_TAG})...${NC}"
    container_build "omnia_auth" "${AUTH_TAG}" \
        "${SCRIPT_DIR}/omnia_auth" "Containerfile"
}

# =============================================================================
# Build summary
# =============================================================================
print_build_summary() {
    echo -e "\n${BLUE}=== OIM BUILD SUMMARY ===${NC}"
    if [ ${#SUCCESSFUL_BUILDS[@]} -ne 0 ]; then
        echo -e "${GREEN}Successfully built: ${YELLOW}${SUCCESSFUL_BUILDS[*]}${NC}"
    fi
    if [ ${#FAILED_BUILDS[@]} -ne 0 ]; then
        echo -e "${RED}Failed: ${MAGENTA}${FAILED_BUILDS[*]}${NC}"
        exit 1
    fi
    if [ ${#SUCCESSFUL_BUILDS[@]} -ne 0 ]; then
        echo -e "\n${GREEN}Next step: ./omnia.sh --install${NC}"
    fi
}

# =============================================================================
# Main — Dispatch
# =============================================================================
echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN} OIM Core — Container Build            ${NC}"
echo -e "${GREEN}=======================================${NC}"
echo -e "${BLUE}Build tool:   ${BUILD_TOOL}${NC}"
echo -e "${BLUE}Build action: ${BUILD_ACTION}${NC}"
echo ""

IFS=',' read -r -a containers <<< "$CONTAINER_ARG"

for container in "${containers[@]}"; do
    case "$container" in
        all)    build_omnia_core; build_omnia_auth ;;
        core)   build_omnia_core ;;
        auth)   build_omnia_auth ;;
        *)
            echo -e "${RED}Error: Unknown container '$container'. Valid: all, core, auth${NC}"
            echo -e "${YELLOW}For other containers use domain-specific build scripts:${NC}"
            echo -e "  Telemetry:      src/telemetry/containers/build_images.sh"
            echo -e "  BuildStream:    src/build_stream/containers/build_images.sh"
            echo -e "  Image Builder:  src/image_build_manager/containers/build_images.sh"
            exit 1
            ;;
    esac
done

print_build_summary
