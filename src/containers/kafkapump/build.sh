#!/bin/bash
# =============================================================================
# kafkapump — Container Build Script (iDRAC Telemetry)
# =============================================================================
# Sourced by build_images.sh. Defines build_kafkapump().
# Requires: iDRAC-Telemetry-Reference-Tools repo clone
# =============================================================================

# iDRAC Telemetry repo settings
IDRAC_TELEMETRY_COMMIT="cfa9102a900a76afe9de578d080e98f685625814"
IDRAC_TELEMETRY_CLONE_DIR=".idrac-telemetry-tools"

build_kafkapump() {
    print_build_info "kafkapump" "${KAFKAPUMP_TAG}" \
        "Using iDRAC Commit: ${YELLOW}${IDRAC_TELEMETRY_COMMIT}${NC}"

    # Clone repo if needed
    clone_repo_at_commit \
        "https://github.com/dell/iDRAC-Telemetry-Reference-Tools.git" \
        "${IDRAC_TELEMETRY_CLONE_DIR}" \
        "${IDRAC_TELEMETRY_COMMIT}"

    container_build \
        "kafkapump" \
        "${KAFKAPUMP_TAG}" \
        "${IDRAC_TELEMETRY_CLONE_DIR}" \
        "docker-compose-files/Dockerfile" \
        "--build-arg CMD=kafkapump"
}
