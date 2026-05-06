#!/bin/bash
#
# pull_benchmarks.sh - Pull and organize HPC benchmark artifacts from local repository
# Usage: ./pull_benchmarks.sh <arch> [config_path]
#   arch: x86_64 or aarch64
#   config_path: Optional path to slurm_custom.json (default: /opt/omnia/config)
#

set -e

ARCH="${1:-x86_64}"
CONFIG_PATH="${2:-/opt/omnia/config}"
HPC_TOOLS_BASE="/hpc_tools"
LOCAL_REPO_BASE="/var/lib/pulp/content"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate architecture
if [[ "${ARCH}" != "x86_64" && "${ARCH}" != "aarch64" ]]; then
    log_error "Invalid architecture: ${ARCH}. Must be x86_64 or aarch64."
    exit 1
fi

# Check if hpc_tools directory exists
if [[ ! -d "${HPC_TOOLS_BASE}" ]]; then
    log_error "hpc_tools base directory does not exist: ${HPC_TOOLS_BASE}"
    log_error "Ensure NFS mount for hpc_tools is available."
    exit 1
fi

# Find slurm_custom.json
SLURM_CUSTOM_FILE=""
for path in "${CONFIG_PATH}/slurm_custom.json" "/etc/omnia/slurm_custom.json" "/opt/omnia/slurm_custom.json"; do
    if [[ -f "${path}" ]]; then
        SLURM_CUSTOM_FILE="${path}"
        break
    fi
done

if [[ -z "${SLURM_CUSTOM_FILE}" ]]; then
    log_error "slurm_custom.json not found in standard locations."
    exit 1
fi

log_info "Using slurm_custom.json: ${SLURM_CUSTOM_FILE}"

# Parse benchmark packages from slurm_custom.json
# Look for packages with type "tarball" or "source"
BENCHMARK_PACKAGES=$(jq -r '.packages[]? | select(.type == "tarball" or .type == "source") | .package' "${SLURM_CUSTOM_FILE}" 2>/dev/null || echo "")

if [[ -z "${BENCHMARK_PACKAGES}" ]]; then
    log_warn "No benchmark packages found in slurm_custom.json."
    exit 0
fi

log_info "Found benchmark packages: ${BENCHMARK_PACKAGES}"

# Function to pull a single benchmark
pull_benchmark() {
    local pkg_name="$1"
    local pkg_info
    local pkg_url
    local pkg_type
    local dest_dir

    pkg_info=$(jq -r ".packages[]? | select(.package == \"${pkg_name}\")" "${SLURM_CUSTOM_FILE}")
    pkg_url=$(echo "${pkg_info}" | jq -r '.url // empty')
    pkg_type=$(echo "${pkg_info}" | jq -r '.type // "source"')

    dest_dir="${HPC_TOOLS_BASE}/${pkg_name}"

    # Create destination directory
    log_info "Creating directory: ${dest_dir}"
    mkdir -p "${dest_dir}"

    # Check if artifact exists in local repo
    # Search in offline_repo structure
    local artifact_path=""
    for search_path in "/var/lib/pulp/content/offline_repo/cluster/${ARCH}/rhel/10.0/source/${pkg_name}" \
                      "/var/lib/pulp/content/offline_repo/cluster/${ARCH}/rhel/10.0/tarball/${pkg_name}" \
                      "${LOCAL_REPO_BASE}/offline_repo/cluster/${ARCH}/rhel/10.0/source/${pkg_name}" \
                      "${LOCAL_REPO_BASE}/offline_repo/cluster/${ARCH}/rhel/10.0/tarball/${pkg_name}"; do
        if [[ -d "${search_path}" ]]; then
            artifact_path="${search_path}"
            break
        fi
    done

    if [[ -z "${artifact_path}" ]]; then
        log_warn "Artifact not found in local repository for ${pkg_name}, skipping."
        return 1
    fi

    # Copy artifacts to destination
    log_info "Copying artifacts from ${artifact_path} to ${dest_dir}"
    cp -r "${artifact_path}"/* "${dest_dir}/" 2>/dev/null || true

    # If URL is provided and local copy failed, attempt direct pull
    if [[ -n "${pkg_url}" && ! -f "${dest_dir}"/* ]]; then
        log_info "Attempting direct pull from URL: ${pkg_url}"
        cd "${dest_dir}"
        if command -v wget &>/dev/null; then
            wget -q "${pkg_url}" -O "${pkg_name}.tar.gz" || log_warn "Failed to download ${pkg_url}"
        elif command -v curl &>/dev/null; then
            curl -sSL "${pkg_url}" -o "${pkg_name}.tar.gz" || log_warn "Failed to download ${pkg_url}"
        fi
    fi

    # Verify files were copied
    if [[ -n "$(ls -A ${dest_dir})" ]]; then
        log_info "Successfully staged ${pkg_name}"
        return 0
    else
        log_warn "No files staged for ${pkg_name}"
        return 1
    fi
}

# Pull each benchmark
SUCCESS_COUNT=0
FAIL_COUNT=0

for pkg in ${BENCHMARK_PACKAGES}; do
    if pull_benchmark "${pkg}"; then
        ((SUCCESS_COUNT++))
    else
        ((FAIL_COUNT++))
    fi
done

log_info "Benchmark staging complete: ${SUCCESS_COUNT} succeeded, ${FAIL_COUNT} failed"

exit 0
