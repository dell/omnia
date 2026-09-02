# Telemetry Containers

This directory contains the build scripts and Containerfiles for building Omnia telemetry container images.

## Quick Start

```bash
# Build all telemetry containers (default: podman + load locally)
./build_images.sh

# Build specific container
./build_images.sh ldms

# Build with docker and push to registry
./build_images.sh all build_tool=docker build_action=push

# Build with custom tag
./build_images.sh ldms ldms_tag=1.2
```

## Container Images

| Container | Purpose | Source | Build Method |
|-----------|---------|--------|--------------|
| `ldms` | OVIS LDMS aggregator | Local Containerfile | `ldms/` subdirectory |

## Architecture

**Orchestrator**: `build_images.sh` is the single entry point for telemetry container builds.

**ldms**:

- Has its own folder with unique Containerfile and configuration
- Built via inline function in `build_images.sh`

## Dependencies

- **For ldms**: Containerfile and configure script are local (copied from omnia-artifactory)

## Build Script Options

```bash
./build_images.sh <container> [parameters]

Containers:
  all                    Build all telemetry containers (default)
  ldms                   Build LDMS aggregator

Parameters:
  build_tool=<tool>       podman | docker (default: podman)
  build_action=<action>   load | push (default: load)
  registry=<url>          Registry URL (default: docker.io/dellhpcomniaaisolution)
  ldms_tag=<tag>          ldms tag (default: 1.1)
```

## Registry

**Default registry**: `docker.io/dellhpcomniaaisolution`

To push to registry, use:
```bash
./build_images.sh all build_tool=docker build_action=push
```

## Directory Structure

```
containers/
├── build_images.sh              # Container build orchestrator
├── README.md                    # This file
└── ldms/                        # LDMS aggregator (unique Containerfile)
    ├── Containerfile.bld_n_run.ubuntu26.04
    ├── configure.aggregator.sh
    └── README.md
```

## See Also

- `ldms/README.md` — Detailed documentation for LDMS container build
