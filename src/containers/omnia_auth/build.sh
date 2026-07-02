#!/bin/bash
# =============================================================================
# omnia_auth — Container Build Script
# =============================================================================
# Sourced by build_images.sh. Defines build_omnia_auth().
# Build context: src/containers/omnia_auth/
# =============================================================================
build_omnia_auth() {
    print_build_info "omnia_auth" "${AUTH_TAG}"

    container_build \
        "omnia_auth" \
        "${AUTH_TAG}" \
        "${CONTAINERS_DIR}/omnia_auth" \
        "Containerfile"
}
