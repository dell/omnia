#!/bin/bash
# =============================================================================
# _common.sh — Shared utilities for container build scripts
# =============================================================================
# Sourced by build_images.sh and per-container build.sh scripts.
# Provides: color codes, status arrays, print_build_info(), container_build()
# =============================================================================

# ── Color codes ──
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[34m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# ── Build status tracking ──
SUCCESSFUL_BUILDS=()
FAILED_BUILDS=()
LOADED_IMAGES=()
PUSHED_IMAGES=()

# ── Resolve paths ──
CONTAINERS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${CONTAINERS_DIR}/../.." && pwd)"

# ── Helper: print build info banner ──
print_build_info() {
    local image_name="$1"
    local image_tag="$2"
    local extra_info="${3:-}"

    echo "Building ${image_name} image..."
    echo -e "Using Build Tool: ${YELLOW}${BUILD_TOOL}${NC}"
    echo -e "Using Build Action: ${YELLOW}${BUILD_ACTION}${NC}"
    echo -e "Using Tag: ${YELLOW}${image_tag}${NC}"
    [ -n "$extra_info" ] && echo -e "$extra_info"
    if [ "$BUILD_TOOL" = "docker" ] && [ "$BUILD_ACTION" = "push" ]; then
        echo -e "Registry: ${YELLOW}${OMNIA_DOCKER_REGISTERY}${NC}"
        echo -e "Full Image Name: ${YELLOW}${OMNIA_DOCKER_REGISTERY}/${image_name}:${image_tag}${NC}"
    fi
    echo -e "${RED}---------------------------------${NC}"
}

# ── Helper: generic container build ──
# Usage: container_build <image_name> <image_tag> <build_dir> <containerfile> [extra_args] [extra_flags] [platform]
#
# Args:
#   image_name   — e.g. "omnia_core", "kafkapump"
#   image_tag    — e.g. "2.2", "1.3"
#   build_dir    — absolute path to build context directory
#   containerfile — Containerfile path (relative to build_dir or absolute)
#   extra_args   — extra build args, e.g. "--build-arg CMD=kafkapump" (optional)
#   extra_flags  — extra flags, e.g. "--network=host" (optional)
#   platform     — platform override, default "linux/amd64" (optional)
container_build() {
    local image_name="$1"
    local image_tag="$2"
    local build_dir="$3"
    local containerfile="$4"
    local extra_args="${5:-}"
    local extra_flags="${6:-}"
    local platform="${7:-linux/amd64}"

    cd "$build_dir" || exit 1

    local BUILD_RESULT
    local IMAGE_DESTINATION

    if [ "$BUILD_TOOL" = "podman" ]; then
        # shellcheck disable=SC2086
        podman build ${extra_args} -t "${image_name}:${image_tag}" -f "${containerfile}" ${extra_flags} .
        BUILD_RESULT=$?
        IMAGE_DESTINATION="Local (Podman): ${image_name}:${image_tag}"
    elif [ "$BUILD_TOOL" = "docker" ]; then
        if [ "$BUILD_ACTION" = "load" ]; then
            # shellcheck disable=SC2086
            docker buildx build --no-cache ${extra_args} -t "${image_name}:${image_tag}" \
                --file "${containerfile}" --platform "${platform}" ${extra_flags} --load .
            BUILD_RESULT=$?
            IMAGE_DESTINATION="Local (Docker): ${image_name}:${image_tag}"
        elif [ "$BUILD_ACTION" = "push" ]; then
            # shellcheck disable=SC2086
            docker buildx build --no-cache ${extra_args} \
                -t "${OMNIA_DOCKER_REGISTERY}/${image_name}:${image_tag}" \
                --file "${containerfile}" --platform "${platform}" \
                --provenance=true --sbom=true ${extra_flags} --push .
            BUILD_RESULT=$?
            IMAGE_DESTINATION="Registry: ${OMNIA_DOCKER_REGISTERY}/${image_name}:${image_tag}"
        else
            echo -e "${RED}Invalid BUILD_ACTION. Please enter 'load' or 'push'.${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Invalid BUILD_TOOL. Please enter 'podman' or 'docker'.${NC}"
        exit 1
    fi

    if [ $BUILD_RESULT -eq 0 ]; then
        echo -e "${GREEN}${image_name} image built successfully.${NC}"
        SUCCESSFUL_BUILDS+=("${image_name}")
        if [ "$BUILD_TOOL" = "docker" ] && [ "$BUILD_ACTION" = "push" ]; then
            PUSHED_IMAGES+=("$IMAGE_DESTINATION")
        else
            LOADED_IMAGES+=("$IMAGE_DESTINATION")
        fi
    else
        echo -e "${RED}${image_name} image build failed.${NC}"
        FAILED_BUILDS+=("${image_name}")
    fi

    cd - > /dev/null || exit 1
}

# ── Helper: clone a git repo at a specific commit ──
# Usage: clone_repo_at_commit <repo_url> <clone_dir> <commit>
clone_repo_at_commit() {
    local repo_url="$1"
    local clone_dir="$2"
    local commit="$3"

    if [ ! -d "$clone_dir" ]; then
        echo -e "${YELLOW}Cloning ${repo_url} at commit ${commit}...${NC}"
        git clone "$repo_url" "$clone_dir"
        cd "$clone_dir" || exit 1
        git fetch --all
        git checkout "$commit"
        cd - > /dev/null || exit 1
        echo -e "${GREEN}Repository cloned and checked out to ${commit}.${NC}"
    else
        echo -e "${YELLOW}$(basename "$clone_dir") already cloned.${NC}"
    fi
}

# ── Helper: print build summary ──
print_build_summary() {
    echo -e "\n${BLUE}=== BUILD SUMMARY ===${NC}"
    if [ ${#SUCCESSFUL_BUILDS[@]} -ne 0 ]; then
        echo -e "${GREEN}Successfully built containers:${YELLOW} ${SUCCESSFUL_BUILDS[*]} ${NC}"

        if [ ${#LOADED_IMAGES[@]} -ne 0 ]; then
            echo -e "\n${BLUE}📦 Images loaded locally:${NC}"
            for image in "${LOADED_IMAGES[@]}"; do
                echo -e "  ${GREEN}✓${NC} ${image}"
            done
        fi

        if [ ${#PUSHED_IMAGES[@]} -ne 0 ]; then
            echo -e "\n${BLUE}🚀 Images pushed to registry:${NC}"
            for image in "${PUSHED_IMAGES[@]}"; do
                echo -e "  ${GREEN}✓${NC} ${image}"
            done
            echo -e "\n${YELLOW}Registry Images Available:${NC}"
            echo -e "You can now pull these images from the registry using:"
            for image in "${PUSHED_IMAGES[@]}"; do
                registry_image=$(echo "$image" | sed 's/Registry: //')
                echo -e "  ${BLUE}docker pull ${registry_image}${NC}"
            done
        fi

        if [[ " ${SUCCESSFUL_BUILDS[*]} " =~ " omnia_core " ]]; then
            echo -e "\n${GREEN}🎉 omnia_core image built successfully!${NC}"
            echo -e "${YELLOW}Next step:${NC}"
            echo -e "Execute the script to create the core container and configure passwordless SSH:"
            echo -e "   ${BLUE}./omnia.sh --install${NC}"
        fi
    fi

    if [ ${#FAILED_BUILDS[@]} -ne 0 ]; then
        echo -e "\n${RED}❌ Failed builds:${MAGENTA} ${FAILED_BUILDS[*]} ${NC}"
        exit 1
    else
        if [ ${#SUCCESSFUL_BUILDS[@]} -ne 0 ]; then
            echo -e "\n${GREEN}🎉 All requested images built successfully!${NC}"
            total_local=${#LOADED_IMAGES[@]}
            total_pushed=${#PUSHED_IMAGES[@]}
            echo -e "\n${BLUE}📊 Build Statistics:${NC}"
            echo -e "  • Total containers built: ${YELLOW}${#SUCCESSFUL_BUILDS[@]}${NC}"
            echo -e "  • Images loaded locally: ${YELLOW}${total_local}${NC}"
            echo -e "  • Images pushed to registry: ${YELLOW}${total_pushed}${NC}"
        fi
    fi
}
