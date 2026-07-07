#!/bin/bash
# =============================================================================
# telemetry_receiver — Container Build Script (iDRAC Telemetry)
# =============================================================================
# Sourced by build_images.sh. Defines build_telemetry_receiver().
# Requires: iDRAC-Telemetry-Reference-Tools repo clone
# =============================================================================

# iDRAC Telemetry repo settings (shared with kafkapump, victoriapump)
IDRAC_TELEMETRY_COMMIT="${IDRAC_TELEMETRY_COMMIT:-cfa9102a900a76afe9de578d080e98f685625814}"
IDRAC_TELEMETRY_CLONE_DIR="${IDRAC_TELEMETRY_CLONE_DIR:-.idrac-telemetry-tools}"

build_telemetry_receiver() {
    print_build_info "idrac_telemetry_receiver" "${TELEMETRY_RECEIVER_TAG}" \
        "Using iDRAC Commit: ${YELLOW}${IDRAC_TELEMETRY_COMMIT}${NC}"

    # Clone repo if needed
    clone_repo_at_commit \
        "https://github.com/dell/iDRAC-Telemetry-Reference-Tools.git" \
        "${IDRAC_TELEMETRY_CLONE_DIR}" \
        "${IDRAC_TELEMETRY_COMMIT}"

    container_build \
        "idrac_telemetry_receiver" \
        "${TELEMETRY_RECEIVER_TAG}" \
        "${IDRAC_TELEMETRY_CLONE_DIR}" \
        "docker-compose-files/Dockerfile.telemetry_receiver"
}
