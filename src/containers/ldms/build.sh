#!/bin/bash
# =============================================================================
# ldms — Container Build Script
# =============================================================================
# Sourced by build_images.sh. Defines build_ldms().
# Build context: src/containers/ldms/
# =============================================================================

build_ldms() {
    print_build_info "ldms" "${LDMS_TAG}"

    container_build \
        "ldms" \
        "${LDMS_TAG}" \
        "${CONTAINERS_DIR}/ldms" \
        "Containerfile.bld_n_run.ubuntu26.04"
}
