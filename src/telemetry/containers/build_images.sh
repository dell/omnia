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
# build_images.sh — Telemetry Container Build (Self-Contained)
# =============================================================================
# Builds the LDMS telemetry container image.
#
# Usage:
#   ./build_images.sh                                        # Build all telemetry containers
#   ./build_images.sh ldms                                   # Build the LDMS container
#   ./build_images.sh ldms ldms_tag=1.2                      # Custom tag
#   ./build_images.sh all build_tool=docker                  # Use docker
#   ./build_images.sh all build_tool=docker build_action=push # Push to registry
#
# Available containers:
#   all, ldms
#
# Parameters:
#   build_tool=<tool>                podman | docker (default: podman)
#   build_action=<action>            load | push (default: load)
#   registry=<url>                   Registry URL (default: docker.io/dellhpcomniaaisolution)
#   ldms_tag=<tag>                   ldms tag (default: 1.1)
# =============================================================================

set -euo pipefail

# ── Resolve paths ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Color codes ──
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[34m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# =============================================================================
# Show help
# =============================================================================
show_help() {
    echo -e "${GREEN}Telemetry Container Build Script${NC}"
    echo -e "${GREEN}======================================${NC}"
    echo ""
    echo -e "${BLUE}USAGE:${NC}"
    echo "  ./build_images.sh [container] [parameters]"
    echo ""
    echo -e "${BLUE}CONTAINERS:${NC}"
    echo "  all                    Build all telemetry containers (default)"
    echo "  ldms                   Build ldms container"
    echo ""
    echo -e "${BLUE}PARAMETERS (key=value format):${NC}"
    echo "  build_tool=<tool>       podman | docker (default: podman)"
    echo "  build_action=<action>   load | push (default: load)"
    echo "  registry=<url>          Registry URL (default: docker.io/dellhpcomniaaisolution)"
    echo "  ldms_tag=<tag>          ldms tag (default: 1.1)"
    echo ""
    echo -e "${BLUE}EXAMPLES:${NC}"
    echo "  ./build_images.sh"
    echo "  ./build_images.sh ldms"
    echo "  ./build_images.sh ldms ldms_tag=1.2"
    echo "  ./build_images.sh all build_tool=docker"
    echo "  ./build_images.sh all build_tool=docker build_action=push"
    echo ""
    echo -e "${BLUE}NOTES:${NC}"
    echo "  - build_action=push requires build_tool=docker"
    echo "  - Default registry: docker.io/dellhpcomniaaisolution"
    exit 0
}

# ── Build status tracking ──
SUCCESSFUL_BUILDS=()
FAILED_BUILDS=()

# =============================================================================
# Default parameterized values
# =============================================================================
BUILD_TOOL="podman"
BUILD_ACTION="load"
OMNIA_DOCKER_REGISTERY="docker.io/dellhpcomniaaisolution"

LDMS_TAG="1.1"

# =============================================================================
# Parse command-line parameters (key=value format)
# =============================================================================
CONTAINER_ARG="${1:-all}"
shift 2>/dev/null || true

for arg in "$@"; do
    case "$arg" in
        build_tool=*)              BUILD_TOOL="${arg#*=}" ;;
        build_action=*)            BUILD_ACTION="${arg#*=}" ;;
        registry=*)                OMNIA_DOCKER_REGISTERY="${arg#*=}" ;;
        ldms_tag=*)                LDMS_TAG="${arg#*=}" ;;
        -h|--help)
            show_help
            ;;
        *)
            echo -e "${RED}Error: Unknown parameter '$arg'${NC}"
            echo -e "${YELLOW}Valid: build_tool, build_action, registry, ldms_tag${NC}"
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
build_ldms() {
    echo -e "${BLUE}Building ldms (tag: ${LDMS_TAG})...${NC}"
    container_build "ldms" "${LDMS_TAG}" \
        "${SCRIPT_DIR}/ldms" "Containerfile.bld_n_run.ubuntu26.04"
}

# =============================================================================
# Build summary
# =============================================================================
print_build_summary() {
    echo -e "\n${BLUE}=== TELEMETRY BUILD SUMMARY ===${NC}"
    if [ ${#SUCCESSFUL_BUILDS[@]} -ne 0 ]; then
        echo -e "${GREEN}Successfully built: ${YELLOW}${SUCCESSFUL_BUILDS[*]}${NC}"
    fi
    if [ ${#FAILED_BUILDS[@]} -ne 0 ]; then
        echo -e "${RED}Failed: ${MAGENTA}${FAILED_BUILDS[*]}${NC}"
        exit 1
    fi
    echo -e "${GREEN}All telemetry containers built successfully.${NC}"
}

# =============================================================================
# Main — Dispatch
# =============================================================================
echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN} Telemetry — Container Build           ${NC}"
echo -e "${GREEN}=======================================${NC}"
echo -e "${BLUE}Build tool:   ${BUILD_TOOL}${NC}"
echo -e "${BLUE}Build action: ${BUILD_ACTION}${NC}"
echo ""

IFS=',' read -r -a containers <<< "$CONTAINER_ARG"

for container in "${containers[@]}"; do
    case "$container" in
        all)
            build_ldms
            ;;
        ldms) build_ldms ;;
        *)
            echo -e "${RED}Error: Unknown container '$container'. Valid: all, ldms${NC}"
            exit 1
            ;;
    esac
done

print_build_summary
