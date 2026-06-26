#!/bin/bash
# =============================================================================
# image_builder — Container Build Script (OpenCHAMI)
# =============================================================================
# Sourced by build_images.sh. Defines build_image_builder().
# Requires: OpenCHAMI/image-builder repo clone + Containerfile.el10 overlay
# =============================================================================

# Image Builder repo settings
IMAGE_BUILDER_COMMIT="70702bd3d76d066d18441bc0b2fbb89020544d8f"
IMAGE_BUILDER_CLONE_DIR=".image-builder-tools"
IMAGE_BUILDER_DIR="${CONTAINERS_DIR}/image_builder"

# Clone and configure the image-builder repo
clone_image_builder_repo() {
    if [ ! -d "$IMAGE_BUILDER_CLONE_DIR" ]; then
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
    else
        echo -e "${YELLOW}OpenCHAMI/image-builder already cloned.${NC}"
    fi
}

build_image_builder() {
    local detected_platform="linux/amd64"

    if [ "$BUILD_TOOL" = "docker" ]; then
        # Dynamic platform detection for image-builder (only when using docker)
        detected_platform="$(docker info --format '{{.OSType}}/{{.Architecture}}')" || {
            echo -e "${RED}Error: Failed to detect platform. Docker info command failed.${NC}"
            echo -e "${YELLOW}Please ensure Docker is installed and running.${NC}"
            exit 1
        }
    fi

    print_build_info "image-build-el10" "${IMAGE_BUILDER_TAG}" \
        "Using Image Builder Commit: ${YELLOW}${IMAGE_BUILDER_COMMIT}${NC}\nUsing Detected Platform: ${YELLOW}${detected_platform}${NC}"

    # Clone repo if needed
    clone_image_builder_repo

    container_build \
        "image-build-el10" \
        "${IMAGE_BUILDER_TAG}" \
        "${IMAGE_BUILDER_CLONE_DIR}" \
        "dockerfiles/dnf/Containerfile.el10" \
        "" \
        "" \
        "${detected_platform}"
}
