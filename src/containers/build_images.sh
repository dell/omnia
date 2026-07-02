#!/bin/bash
# =============================================================================
# build_images.sh — Container Image Build Wrapper
# =============================================================================
# Entry point for building all Omnia container images.
# Delegates to per-container build.sh scripts in each subdirectory.
#
# Usage:
#   ./build_images.sh [container] [param=value ...]
#   ./build_images.sh oim                         # core + auth + image-builder (default)
#   ./build_images.sh all                         # all containers
#   ./build_images.sh core build_tool=docker      # single container
#   ./build_images.sh core,auth                   # comma-separated
#
# Available containers:
#   oim, all, core, auth, ldms, pipeline, telemetry,
#   kafkapump, victoriapump, telemetry-receiver, image-builder, build-stream
# =============================================================================

# ── Source shared utilities ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "${SCRIPT_DIR}/_common.sh"

# ── Source per-container build scripts ──
source "${SCRIPT_DIR}/omnia_core/build.sh"
source "${SCRIPT_DIR}/omnia_auth/build.sh"
source "${SCRIPT_DIR}/omnia_build_stream/build.sh"
source "${SCRIPT_DIR}/ldms/build.sh"
source "${SCRIPT_DIR}/kafkapump/build.sh"
source "${SCRIPT_DIR}/victoriapump/build.sh"
source "${SCRIPT_DIR}/telemetry_receiver/build.sh"
source "${SCRIPT_DIR}/image_builder/build.sh"

# ── Install git if not present ──
echo -e "${BLUE}Installing git...${NC}"
dnf install -y git
echo -e "${GREEN}Git installation complete.${NC}\n"

# =============================================================================
# Default parameterized values
# =============================================================================
BUILD_TOOL="podman"
BUILD_ACTION="load"
OMNIA_DOCKER_REGISTERY="docker.io/dellhpcomniaaisolution"

# Default image tags for each container (can be overridden individually)
CORE_TAG="2.2"
AUTH_TAG="1.1"
LDMS_TAG="1.1"
KAFKAPUMP_TAG="1.3"
VICTORIAPUMP_TAG="1.3"
TELEMETRY_RECEIVER_TAG="1.3"
IMAGE_BUILDER_TAG="1.1"
BUILD_STREAM_TAG="1.1"

# Valid parameter names
VALID_PARAMS=("build_tool" "build_action" "core_tag" "auth_tag" "ldms_tag" "kafkapump_tag" "victoriapump_tag" "telemetry_receiver_tag" "image_builder_tag" "build_stream_tag")

VALID_CONTAINERS=("all" "core" "auth" "ldms" "pipeline" "telemetry" "kafkapump" "victoriapump" "telemetry-receiver" "image-builder" "build-stream")

# Common parameters valid for all container types
COMMON_PARAMS=("build_tool" "build_action")

# Store container-specific parameters for later validation
CONTAINER_PARAMS=()
INVALID_PARAMS=()

# =============================================================================
# Parse command line arguments — first pass to collect parameters
# =============================================================================
for arg in "$@"; do
    if [[ "$arg" != *"="* ]]; then
        continue
    fi

    param_name="${arg%%=*}"

    if [[ ! " ${VALID_PARAMS[@]} " =~ " ${param_name} " ]]; then
        INVALID_PARAMS+=("$param_name")
    fi

    CONTAINER_PARAMS+=("$param_name")

    if [[ "$arg" =~ ^build_tool=.*$ ]]; then
        BUILD_TOOL="${arg#build_tool=}"
    elif [[ "$arg" =~ ^build_action=.*$ ]]; then
        BUILD_ACTION="${arg#build_action=}"
    elif [[ "$arg" =~ ^core_tag=.*$ ]]; then
        CORE_TAG="${arg#core_tag=}"
    elif [[ "$arg" =~ ^auth_tag=.*$ ]]; then
        AUTH_TAG="${arg#auth_tag=}"
    elif [[ "$arg" =~ ^ldms_tag=.*$ ]]; then
        LDMS_TAG="${arg#ldms_tag=}"
    elif [[ "$arg" =~ ^kafkapump_tag=.*$ ]]; then
        KAFKAPUMP_TAG="${arg#kafkapump_tag=}"
    elif [[ "$arg" =~ ^victoriapump_tag=.*$ ]]; then
        VICTORIAPUMP_TAG="${arg#victoriapump_tag=}"
    elif [[ "$arg" =~ ^telemetry_receiver_tag=.*$ ]]; then
        TELEMETRY_RECEIVER_TAG="${arg#telemetry_receiver_tag=}"
    elif [[ "$arg" =~ ^image_builder_tag=.*$ ]]; then
        IMAGE_BUILDER_TAG="${arg#image_builder_tag=}"
    elif [[ "$arg" =~ ^build_stream_tag=.*$ ]]; then
        BUILD_STREAM_TAG="${arg#build_stream_tag=}"
    fi
done

# =============================================================================
# Validate inputs
# =============================================================================
if [[ "$BUILD_TOOL" != "podman" && "$BUILD_TOOL" != "docker" ]]; then
    echo -e "${RED}Error: Invalid build_tool value '${BUILD_TOOL}'${NC}"
    echo -e "${YELLOW}Valid values are: podman, docker${NC}"
    exit 1
fi

if [[ "$BUILD_ACTION" != "load" && "$BUILD_ACTION" != "push" ]]; then
    echo -e "${RED}Error: Invalid build_action value '${BUILD_ACTION}'${NC}"
    echo -e "${YELLOW}Valid values are: load, push${NC}"
    exit 1
fi

if [[ "$BUILD_ACTION" == "push" && "$BUILD_TOOL" != "docker" ]]; then
    echo -e "${RED}Error: build_action=push requires build_tool=docker${NC}"
    echo -e "${YELLOW}Please set build_tool=docker when using build_action=push${NC}"
    exit 1
fi

# =============================================================================
# Validate container-specific parameters
# =============================================================================
validate_container_params() {
    local container=$1
    local allowed_params=("${@:2}")

    for param in "${CONTAINER_PARAMS[@]}"; do
        if [[ " ${COMMON_PARAMS[@]} " =~ " ${param} " ]]; then
            continue
        fi
        if [[ ! " ${allowed_params[@]} " =~ " ${param} " ]]; then
            echo -e "${RED}Error: Parameter '${param}' is not valid for container '${container}'${NC}"
            echo -e "${YELLOW}Valid parameters for '${container}': ${COMMON_PARAMS[*]} ${allowed_params[*]}${NC}"
            exit 1
        fi
    done
}

# =============================================================================
# Dispatch — select which containers to build
# =============================================================================
CONTAINER_ARG="${1:-oim}"

case "$CONTAINER_ARG" in
    oim)
        ALLOWED_TAG_PARAMS=("core_tag" "auth_tag" "image_builder_tag")
        if [ ${#INVALID_PARAMS[@]} -ne 0 ]; then
            echo -e "${RED}Error: Invalid parameter(s): ${INVALID_PARAMS[*]}${NC}"
            echo -e "${YELLOW}Valid parameters for 'oim': ${COMMON_PARAMS[*]} ${ALLOWED_TAG_PARAMS[*]}${NC}"
            exit 1
        fi
        validate_container_params "oim" "${ALLOWED_TAG_PARAMS[@]}"
        build_omnia_core
        build_omnia_auth
        build_image_builder
        ;;

    all)
        ALLOWED_TAG_PARAMS=("core_tag" "auth_tag" "ldms_tag" "kafkapump_tag" "victoriapump_tag" "telemetry_receiver_tag" "image_builder_tag")
        if [ ${#INVALID_PARAMS[@]} -ne 0 ]; then
            echo -e "${RED}Error: Invalid parameter(s): ${INVALID_PARAMS[*]}${NC}"
            echo -e "${YELLOW}Valid parameters for 'all': ${COMMON_PARAMS[*]} ${ALLOWED_TAG_PARAMS[*]}${NC}"
            exit 1
        fi
        validate_container_params "all" "${ALLOWED_TAG_PARAMS[@]}"
        build_omnia_core
        build_omnia_auth
        build_ldms
        build_kafkapump
        build_victoriapump
        build_telemetry_receiver
        build_image_builder
        ;;

    pipeline)
        ALLOWED_TAG_PARAMS=("core_tag" "auth_tag" "ldms_tag" "kafkapump_tag" "victoriapump_tag" "telemetry_receiver_tag" "image_builder_tag")
        if [ ${#INVALID_PARAMS[@]} -ne 0 ]; then
            echo -e "${RED}Error: Invalid parameter(s): ${INVALID_PARAMS[*]}${NC}"
            echo -e "${YELLOW}Valid parameters for 'pipeline': ${COMMON_PARAMS[*]} ${ALLOWED_TAG_PARAMS[*]}${NC}"
            exit 1
        fi
        validate_container_params "pipeline" "${ALLOWED_TAG_PARAMS[@]}"
        build_omnia_core
        build_omnia_auth
        build_ldms
        build_kafkapump
        build_victoriapump
        build_telemetry_receiver
        build_image_builder
        ;;

    telemetry)
        ALLOWED_TAG_PARAMS=("kafkapump_tag" "victoriapump_tag" "telemetry_receiver_tag")
        if [ ${#INVALID_PARAMS[@]} -ne 0 ]; then
            echo -e "${RED}Error: Invalid parameter(s): ${INVALID_PARAMS[*]}${NC}"
            echo -e "${YELLOW}Valid parameters for 'telemetry': ${COMMON_PARAMS[*]} ${ALLOWED_TAG_PARAMS[*]}${NC}"
            exit 1
        fi
        validate_container_params "telemetry" "${ALLOWED_TAG_PARAMS[@]}"
        build_kafkapump
        build_victoriapump
        build_telemetry_receiver
        ;;

    image-builder)
        ALLOWED_TAG_PARAMS=("image_builder_tag")
        if [ ${#INVALID_PARAMS[@]} -ne 0 ]; then
            echo -e "${RED}Error: Invalid parameter(s): ${INVALID_PARAMS[*]}${NC}"
            echo -e "${YELLOW}Valid parameters for 'image-builder': ${COMMON_PARAMS[*]} ${ALLOWED_TAG_PARAMS[*]}${NC}"
            exit 1
        fi
        validate_container_params "image-builder" "${ALLOWED_TAG_PARAMS[@]}"
        build_image_builder
        ;;

    build-stream)
        ALLOWED_TAG_PARAMS=("build_stream_tag")
        if [ ${#INVALID_PARAMS[@]} -ne 0 ]; then
            echo -e "${RED}Error: Invalid parameter(s): ${INVALID_PARAMS[*]}${NC}"
            echo -e "${YELLOW}Valid parameters for 'build-stream': ${COMMON_PARAMS[*]} ${ALLOWED_TAG_PARAMS[*]}${NC}"
            exit 1
        fi
        validate_container_params "build-stream" "${ALLOWED_TAG_PARAMS[@]}"
        build_omnia_build_stream
        ;;

    *)
        # Handle individual containers or comma-separated lists
        IFS=',' read -r -a containers <<< "$CONTAINER_ARG"

        ALLOWED_TAG_PARAMS=()
        BUILDING_CORE=false

        for container in "${containers[@]}"; do
            case "$container" in
                all)       ALLOWED_TAG_PARAMS+=("core_tag" "auth_tag" "ldms_tag" "kafkapump_tag" "victoriapump_tag" "telemetry_receiver_tag"); BUILDING_CORE=true ;;
                oim)       ALLOWED_TAG_PARAMS+=("core_tag" "auth_tag" "image_builder_tag"); BUILDING_CORE=true ;;
                core)      ALLOWED_TAG_PARAMS+=("core_tag"); BUILDING_CORE=true ;;
                auth)      ALLOWED_TAG_PARAMS+=("auth_tag") ;;
                ldms)              ALLOWED_TAG_PARAMS+=("ldms_tag") ;;
                pipeline)          ALLOWED_TAG_PARAMS+=("core_tag" "auth_tag" "ldms_tag" "kafkapump_tag" "victoriapump_tag" "telemetry_receiver_tag"); BUILDING_CORE=true ;;
                telemetry)         ALLOWED_TAG_PARAMS+=("kafkapump_tag" "victoriapump_tag" "telemetry_receiver_tag") ;;
                kafkapump)         ALLOWED_TAG_PARAMS+=("kafkapump_tag") ;;
                victoriapump)      ALLOWED_TAG_PARAMS+=("victoriapump_tag") ;;
                telemetry-receiver) ALLOWED_TAG_PARAMS+=("telemetry_receiver_tag") ;;
                image-builder)     ALLOWED_TAG_PARAMS+=("image_builder_tag") ;;
                build-stream)      ALLOWED_TAG_PARAMS+=("build_stream_tag") ;;
                *)
                    echo -e "${RED}Invalid container: $container. Available options: oim, all, core, auth, ldms, pipeline, telemetry, kafkapump, victoriapump, telemetry-receiver, image-builder, build-stream.${NC}"
                    exit 1
                    ;;
            esac
        done

        if [ ${#INVALID_PARAMS[@]} -ne 0 ]; then
            echo -e "${RED}Error: Invalid parameter(s): ${INVALID_PARAMS[*]}${NC}"
            echo -e "${YELLOW}Valid parameters for '$1': ${COMMON_PARAMS[*]} ${ALLOWED_TAG_PARAMS[*]}${NC}"
            exit 1
        fi
        validate_container_params "$1" "${ALLOWED_TAG_PARAMS[@]}"

        for container in "${containers[@]}"; do
            case "$container" in
                all)       build_omnia_core; build_omnia_auth; build_ldms; build_kafkapump; build_victoriapump; build_telemetry_receiver; build_omnia_build_stream ;;
                oim)       build_omnia_core; build_omnia_auth; build_image_builder; build_omnia_build_stream ;;
                core)      build_omnia_core ;;
                auth)      build_omnia_auth ;;
                ldms)              build_ldms ;;
                pipeline)          build_omnia_core; build_omnia_auth; build_ldms; build_kafkapump; build_victoriapump; build_telemetry_receiver; build_omnia_build_stream ;;
                telemetry)         build_kafkapump; build_victoriapump; build_telemetry_receiver ;;
                kafkapump)         build_kafkapump ;;
                victoriapump)      build_victoriapump ;;
                telemetry-receiver) build_telemetry_receiver ;;
                image-builder)     build_image_builder ;;
                build-stream)      build_omnia_build_stream ;;
            esac
        done
        ;;
esac

# =============================================================================
# Build Summary
# =============================================================================
print_build_summary
