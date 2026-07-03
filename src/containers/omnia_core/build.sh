#!/bin/bash
# =============================================================================
# omnia_core — Container Build Script
# =============================================================================
# Sourced by build_images.sh. Defines build_omnia_core().
# Build context: repo root (for COPY src/ /omnia/src/)
# =============================================================================

build_omnia_core() {
    print_build_info "omnia_core" "${CORE_TAG}"

    container_build \
        "omnia_core" \
        "${CORE_TAG}" \
        "${REPO_ROOT}" \
        "src/containers/omnia_core/Containerfile"
}
