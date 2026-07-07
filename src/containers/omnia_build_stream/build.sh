#!/bin/bash
# =============================================================================
# omnia_build_stream — Container Build Script
# =============================================================================
# Sourced by build_images.sh. Defines build_omnia_build_stream().
# Build context: src/containers/omnia_build_stream/
# Note: Uses --network=host for docker builds
# =============================================================================

build_omnia_build_stream() {
    print_build_info "omnia_build_stream" "${BUILD_STREAM_TAG}"

    container_build \
        "omnia_build_stream" \
        "${BUILD_STREAM_TAG}" \
        "${CONTAINERS_DIR}/omnia_build_stream" \
        "Containerfile" \
        "" \
        "--network=host"
}
