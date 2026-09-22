#!/bin/bash

# Check LDMS_REPO variable
if [ -z "$LDMS_REPO" ] ; then
    echo "Set path to your clone of https://github.com/ovis-hpc/ovis.git:
Run command: export LDMS_REPO=<PATH_TO_LDMS_CLONE>
"
    exit 1
fi

# Input validation functions
validate_repo_url() {
    local url="$1"
    # Must be valid URL format (http/https)
    if [[ ! $url =~ ^https?://[a-zA-Z0-9._/-]+$ ]]; then
        echo "Error: Invalid repo URL format" >&2
        return 1
    fi
}

validate_repo_name() {
    local name="$1"
    # Alphanumeric, underscore, dash only
    if [[ ! $name =~ ^[a-zA-Z0-9_-]+$ ]]; then
        echo "Error: Invalid repo name format" >&2
        return 1
    fi
}

# Take inputs
if [ $# -lt 2 ]; then
    echo "Warning: slurm repo_url and slurm repo_name are not set"
fi

REPO_URL="$1"
REPO_NAME="$2"

# Validate inputs if provided
if [[ -n "$REPO_URL" ]]; then
    if ! validate_repo_url "$REPO_URL"; then
        exit 1
    fi
fi

if [[ -n "$REPO_NAME" ]]; then
    if ! validate_repo_name "$REPO_NAME"; then
        exit 1
    fi
fi

export LDMS_REPO="$(readlink -f "$LDMS_REPO")"

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Detect or allow manual architecture selection
ARCH=$(uname -m)

# Normalize and validate architecture
case "$ARCH" in
    x86_64|amd64)
        ARCH_NAME="x86_64"
        ;;
    aarch64|arm64)
        ARCH_NAME="aarch64"
        ;;
    *)
        echo "Unsupported architecture: $ARCH"
        echo "Usage: $0 [x86_64|aarch64]"
        exit 1
        ;;
esac

echo "Detected/Selected architecture: $ARCH_NAME"
echo
echo "Start build container. From there: pushd /builds/ovis/ && /builds/scripts/build_ldms.rockylinux10.bash"

if [[ -z "$REPO_URL" && -z "$REPO_NAME" ]]; then
  echo "Warning: SLURM_REPO_URL and SLURM_REPO_NAME must be provided."
   podman run -it --rm \
    --arch "$ARCH_NAME" \
    --mount type=bind,source="$LDMS_REPO",target=/builds/ovis,z \
    --mount type=bind,source="$SCRIPT_DIR",target=/builds/scripts,z \
    rockylinux:10.0 \
    bash -c '
        echo "Running LDMS build..."
        pushd /builds/ovis/ && /builds/scripts/build_ldms.rockylinux10.bash
    '
else
    podman run -it --rm \
    --arch "$ARCH_NAME" \
    --mount type=bind,source="$LDMS_REPO",target=/builds/ovis,z \
    --mount type=bind,source="$SCRIPT_DIR",target=/builds/scripts,z \
    -e REPO_URL="$REPO_URL" \
    -e REPO_NAME="$REPO_NAME" \
    rockylinux:10.0 \
    bash -c '
        echo "Configuring repo inside container..."
        cat > /etc/yum.repos.d/"${REPO_NAME}".repo <<EOF
[${REPO_NAME}]
name=${REPO_NAME}
baseurl=${REPO_URL}
enabled=1
gpgcheck=0
EOF

        dnf clean all && dnf repolist

        echo "Running LDMS build..."
        pushd /builds/ovis/ && /builds/scripts/build_ldms.rockylinux10.bash
    '
fi
