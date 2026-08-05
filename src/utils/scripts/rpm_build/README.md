# Omnia RPM Build

Build custom RPM packages for Omnia components. Currently supports LDMS (OVIS) RPM builds.

## Quick Start

```bash
# Build LDMS RPM with Slurm metrics support
./build_rpm.sh -u <SLURM_REPO_URL> -n <SLURM_REPO_NAME>

# Build LDMS RPM without Slurm (warning: no slurm metrics)
./build_rpm.sh

# Specify LDMS version
./build_rpm.sh -v 4.5.2 -u <SLURM_REPO_URL> -n <SLURM_REPO_NAME>
```

## Directory Layout

```
src/rpm_build/
├── build_rpm.sh                             # Entry point — clones OVIS, dispatches build
├── README.md                                # This file
└── ldms/
    ├── start_build_container.rockylinux10.bash  # Launches Podman container for RPM build
    ├── build_ldms.rockylinux10.bash              # LDMS build script (runs inside container)
    ├── configure.sh                              # LDMS configure options
    └── rpm_postuninstall.txt                     # RPM post-uninstall scriptlet
```

## How It Works

1. **`build_rpm.sh`** clones the [OVIS repository](https://github.com/ovis-hpc/ovis.git) at the specified version tag
2. **`start_build_container.rockylinux10.bash`** launches a Rocky Linux 10 Podman container with the OVIS source mounted
3. Inside the container, **`build_ldms.rockylinux10.bash`** compiles LDMS and produces the RPM

The build runs inside a container to ensure a clean, reproducible environment.

## Architecture Support

The build script auto-detects the host architecture via `uname -m`:

| Host Architecture | Podman `--arch` | Supported |
|-------------------|----------------|-----------|
| x86_64 / amd64 | `x86_64` | Yes |
| aarch64 / arm64 | `aarch64` | Yes |

No separate scripts are needed — the same `start_build_container.rockylinux10.bash` handles both.

## Parameters

| Parameter | Flag | Default | Description |
|-----------|------|---------|-------------|
| LDMS version | `-v`, `--version` | `4.5.2` | OVIS LDMS version tag to build |
| Slurm repo URL | `-u`, `--url` | — | YUM repo URL for Slurm (required for Slurm metrics) |
| Slurm repo name | `-n`, `--name` | — | YUM repo name for Slurm |

```bash
# Positional arguments also supported
./build_rpm.sh <SLURM_REPO_URL> <SLURM_REPO_NAME>
```

## Prerequisites

- **Podman** installed on the build host
- Internet access to clone OVIS and pull the Rocky Linux 10 base image
- (Optional) Slurm YUM repository URL for Slurm metrics support

## Output

The built RPM is produced inside the container under the OVIS build directory.
Bind-mounted paths ensure the output is accessible on the host after the build completes.

## Relationship to Container Builds

| What | Where | Purpose |
|------|-------|---------|
| Container images | `src/containers/` | Build Omnia container images (omnia_core, ldms, etc.) |
| RPM packages | `src/rpm_build/` | Build standalone RPM packages for node installation |

The LDMS **container** image (built via `src/containers/ldms/`) and the LDMS **RPM** (built here)
serve different deployment models:
- **Container**: LDMS aggregator running as a container on the OIM
- **RPM**: LDMS sampler installed directly on compute nodes
