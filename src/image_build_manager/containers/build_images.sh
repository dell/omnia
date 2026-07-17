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
# build_images.sh — Image Build Manager Container Build (Self-Contained)
# =============================================================================
# Builds the image-builder container used by image_build_manager to create
# OS boot images (kernel, initramfs, rootfs) for x86_64 and aarch64.
#
# Usage:
#   ./build_images.sh                                        # Build for current arch (default)
#   ./build_images.sh image_builder_tag=1.3                  # Custom tag
#   ./build_images.sh build_tool=docker                      # Use docker instead of podman
#   ./build_images.sh build_tool=docker build_action=push    # Push to registry
#   ./build_images.sh registry=myregistry.io/myrepo          # Custom registry
#
# Container names (auto-detected based on host architecture):
#   image-build-el10      — x86_64 image builder
#   image-build-aarch64   — aarch64 image builder
#
# Parameters:
#   image_builder_tag=<tag>    Image tag (default: 1.2)
#   build_tool=<tool>          podman | docker (default: podman)
#   build_action=<action>      load | push (default: load)
#   registry=<url>             Registry URL (default: docker.io/dellhpcomniaaisolution)
# =============================================================================

set -euo pipefail

# ── Resolve paths ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_BUILDER_DIR="${SCRIPT_DIR}/image_builder"

# ── Color codes ──
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── Image Builder repo settings ──
IMAGE_BUILDER_COMMIT="70702bd3d76d066d18441bc0b2fbb89020544d8f"
IMAGE_BUILDER_CLONE_DIR="${SCRIPT_DIR}/.image-builder-tools"

# =============================================================================
# Show help
# =============================================================================
show_help() {
    echo -e "${GREEN}Image Build Manager Container Build Script${NC}"
    echo -e "${GREEN}======================================${NC}"
    echo ""
    echo -e "${BLUE}USAGE:${NC}"
    echo "  ./build_images.sh [parameters]"
    echo ""
    echo -e "${BLUE}PARAMETERS (key=value format):${NC}"
    echo "  image_builder_tag=<tag>    Image tag (default: 1.2)"
    echo "  build_tool=<tool>          podman | docker (default: podman)"
    echo "  build_action=<action>      load | push (default: load)"
    echo "  registry=<url>             Registry URL (default: docker.io/dellhpcomniaaisolution)"
    echo ""
    echo -e "${BLUE}CONTAINER NAMES (auto-detected):${NC}"
    echo "  image-build-el10      — x86_64 image builder"
    echo "  image-build-aarch64   — aarch64 image builder"
    echo ""
    echo -e "${BLUE}EXAMPLES:${NC}"
    echo "  ./build_images.sh"
    echo "  ./build_images.sh image_builder_tag=1.3"
    echo "  ./build_images.sh build_tool=docker"
    echo "  ./build_images.sh build_tool=docker build_action=push"
    echo "  ./build_images.sh registry=myregistry.io/myrepo"
    echo ""
    echo -e "${BLUE}NOTES:${NC}"
    echo "  - build_action=push requires build_tool=docker"
    echo "  - Default registry: docker.io/dellhpcomniaaisolution"
    echo "  - Container name auto-detected based on host architecture"
    echo "  - Clones OpenCHAMI/image-builder repo at commit: ${IMAGE_BUILDER_COMMIT}"
    echo "  - Builds OS boot images (kernel, initramfs, rootfs) for x86_64/aarch64"
    exit 0
}

# =============================================================================
# Default parameterized values
# =============================================================================
BUILD_TOOL="podman"
BUILD_ACTION="load"
OMNIA_DOCKER_REGISTERY="docker.io/dellhpcomniaaisolution"
IMAGE_BUILDER_TAG="1.2"

# =============================================================================
# Parse command-line parameters (key=value format)
# =============================================================================
for arg in "$@"; do
    case "$arg" in
        build_tool=*)         BUILD_TOOL="${arg#*=}" ;;
        build_action=*)       BUILD_ACTION="${arg#*=}" ;;
        registry=*)           OMNIA_DOCKER_REGISTERY="${arg#*=}" ;;
        image_builder_tag=*)  IMAGE_BUILDER_TAG="${arg#*=}" ;;
        -h|--help)
            show_help
            ;;
        *)
            echo -e "${RED}Error: Unknown parameter '$arg'${NC}"
            echo -e "${YELLOW}Valid parameters: image_builder_tag, build_tool, build_action, registry${NC}"
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
# Clone and configure the OpenCHAMI image-builder repo
# =============================================================================
clone_image_builder_repo() {
    if [ -d "$IMAGE_BUILDER_CLONE_DIR" ]; then
        echo -e "${YELLOW}OpenCHAMI/image-builder already cloned.${NC}"
        return
    fi

    echo -e "${YELLOW}Cloning OpenCHAMI/image-builder at commit ${IMAGE_BUILDER_COMMIT}...${NC}"
    git clone "https://github.com/OpenCHAMI/image-builder.git" "$IMAGE_BUILDER_CLONE_DIR"
    cd "$IMAGE_BUILDER_CLONE_DIR" || exit 1
    git fetch --all
    git checkout "$IMAGE_BUILDER_COMMIT"

    # Copy Containerfile.el10 from image_builder/
    echo -e "${YELLOW}Copying Containerfile.el10 to dockerfiles/dnf/...${NC}"
    cp "${IMAGE_BUILDER_DIR}/Containerfile.el10" "dockerfiles/dnf/Containerfile.el10"

    # Copy requirements.txt from image_builder/
    echo -e "${YELLOW}Copying requirements.txt from image_builder/...${NC}"
    cp "${IMAGE_BUILDER_DIR}/requirements.txt" "requirements.txt"

    # Modify utils.py to remove Setting from import
    echo -e "${YELLOW}Modifying src/utils.py import statement...${NC}"
    sed -i 's/from ansible.config.manager import ConfigManager, Setting/from ansible.config.manager import ConfigManager/' src/utils.py

    cd - > /dev/null || exit 1
    echo -e "${GREEN}Repository cloned and configured at ${IMAGE_BUILDER_COMMIT}.${NC}"
}

# =============================================================================
# Container build function (self-contained — no _common.sh dependency)
# =============================================================================
# Usage: container_build <image_name> <image_tag> <build_dir> <containerfile> [platform]
container_build() {
    local image_name="$1"
    local image_tag="$2"
    local build_dir="$3"
    local containerfile="$4"
    local platform="${5:-linux/amd64}"

    cd "$build_dir" || exit 1

    local BUILD_RESULT

    if [ "$BUILD_TOOL" = "podman" ]; then
        podman build -t "${image_name}:${image_tag}" -f "${containerfile}" .
        BUILD_RESULT=$?
    elif [ "$BUILD_TOOL" = "docker" ]; then
        if [ "$BUILD_ACTION" = "load" ]; then
            docker buildx build --no-cache -t "${image_name}:${image_tag}" \
                --file "${containerfile}" --platform "${platform}" --load .
            BUILD_RESULT=$?
        elif [ "$BUILD_ACTION" = "push" ]; then
            docker buildx build --no-cache \
                -t "${OMNIA_DOCKER_REGISTERY}/${image_name}:${image_tag}" \
                --file "${containerfile}" --platform "${platform}" \
                --provenance=true --sbom=true --push .
            BUILD_RESULT=$?
        fi
    fi

    cd - > /dev/null || exit 1

    if [ $BUILD_RESULT -eq 0 ]; then
        echo -e "${GREEN}${image_name}:${image_tag} built successfully.${NC}"
        if [ "$BUILD_TOOL" = "docker" ] && [ "$BUILD_ACTION" = "push" ]; then
            echo -e "${GREEN}Pushed: ${OMNIA_DOCKER_REGISTERY}/${image_name}:${image_tag}${NC}"
        fi
    else
        echo -e "${RED}${image_name}:${image_tag} build FAILED.${NC}"
        exit 1
    fi
}

# =============================================================================
# Build image-builder container
# =============================================================================
build_image_builder() {
    # Detect host architecture
    local host_arch
    host_arch="$(uname -m)"

    local image_name
    local detected_platform

    case "$host_arch" in
        x86_64|amd64)
            image_name="image-build-el10"
            detected_platform="linux/amd64"
            ;;
        aarch64|arm64)
            image_name="image-build-aarch64"
            detected_platform="linux/arm64"
            ;;
        *)
            echo -e "${RED}Error: Unsupported architecture '${host_arch}'.${NC}"
            echo -e "${YELLOW}Supported: x86_64, aarch64${NC}"
            exit 1
            ;;
    esac

    if [ "$BUILD_TOOL" = "docker" ]; then
        detected_platform="$(docker info --format '{{.OSType}}/{{.Architecture}}')" || {
            echo -e "${RED}Error: Failed to detect platform. Docker not running?${NC}"
            exit 1
        }
        case "$detected_platform" in
            */arm64|*/aarch64) image_name="image-build-aarch64" ;;
            *)                 image_name="image-build-el10" ;;
        esac
    fi

    echo -e "${BLUE}Container:  ${image_name}${NC}"
    echo -e "${BLUE}Tag:        ${IMAGE_BUILDER_TAG}${NC}"
    echo -e "${BLUE}Platform:   ${detected_platform}${NC}"
    echo -e "${BLUE}Commit:     ${IMAGE_BUILDER_COMMIT}${NC}"
    echo -e "${RED}---------------------------------${NC}"

    # Clone repo if needed
    clone_image_builder_repo

    container_build \
        "${image_name}" \
        "${IMAGE_BUILDER_TAG}" \
        "${IMAGE_BUILDER_CLONE_DIR}" \
        "dockerfiles/dnf/Containerfile.el10" \
        "${detected_platform}"
}

# =============================================================================
# Main
# =============================================================================
echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN} Image Build Manager — Container Build ${NC}"
echo -e "${GREEN}=======================================${NC}"
echo -e "${BLUE}Build tool:   ${BUILD_TOOL}${NC}"
echo -e "${BLUE}Build action: ${BUILD_ACTION}${NC}"
echo -e "${BLUE}Tag:          ${IMAGE_BUILDER_TAG}${NC}"
echo -e "${BLUE}Registry:     ${OMNIA_DOCKER_REGISTERY}${NC}"
echo ""

build_image_builder

echo -e "\n${GREEN}Image Build Manager container build complete.${NC}"
