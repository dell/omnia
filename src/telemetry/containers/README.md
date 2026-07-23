# Telemetry Containers

This directory contains the build scripts and Containerfiles for building Omnia telemetry container images.

## Quick Start

```bash
# Build all telemetry containers (default: podman + load locally)
./build_images.sh

# Build specific container
./build_images.sh ldms
./build_images.sh kafkapump
./build_images.sh victoriapump
./build_images.sh telemetry-receiver

# Build multiple containers (comma-separated)
./build_images.sh kafkapump,ldms

# Build with docker and push to registry
./build_images.sh all build_tool=docker build_action=push

# Build with custom tag
./build_images.sh kafkapump kafkapump_tag=1.4
```

## Container Images

| Container | Purpose | Source | Build Method |
|-----------|---------|--------|--------------|
| `idrac_telemetry_receiver` | Redfish SSE receiver | iDRAC-Telemetry-Reference-Tools | Inline in `build_images.sh` |
| `kafkapump` | Kafka pump (iDRAC → Kafka) | iDRAC-Telemetry-Reference-Tools | Inline in `build_images.sh` |
| `victoriapump` | Victoria pump (iDRAC → VictoriaMetrics) | iDRAC-Telemetry-Reference-Tools | Inline in `build_images.sh` |
| `ldms` | OVIS LDMS aggregator | Local Containerfile | `ldms/` subdirectory |

## Architecture

**Orchestrator**: `build_images.sh` is the single entry point for all container builds.

**iDRAC containers** (kafkapump, victoriapump, idrac_telemetry_receiver):
- Built inline via functions in `build_images.sh`
- Share the same source repository: `iDRAC-Telemetry-Reference-Tools`
- Auto-cloned into `.idrac-telemetry-tools/` directory
- Differ only in build arguments (CMD arg or Dockerfile name)

**ldms**:
- Has its own folder with unique Containerfile and configuration
- Built via inline function in `build_images.sh`

## Dependencies

- **For iDRAC containers**:
  - Auto-clones `iDRAC-Telemetry-Reference-Tools` into `.idrac-telemetry-tools/`
  - Repository URL: `https://github.com/dell/iDRAC-Telemetry-Reference-Tools.git`
  - Fixed commit: `cfa9102a900a76afe9de578d080e98f685625814`
  - **To update iDRAC commit**: Edit `IDRAC_TELEMETRY_COMMIT` in `build_images.sh`

- **For ldms**: Containerfile and configure script are local (copied from omnia-artifactory)

## Build Script Options

```bash
./build_images.sh <container> [parameters]

Containers:
  all                    Build all telemetry containers (default)
  kafkapump              Build Kafka pump
  victoriapump           Build Victoria pump
  telemetry-receiver     Build iDRAC receiver
  ldms                   Build LDMS aggregator

Parameters:
  build_tool=<tool>       podman | docker (default: podman)
  build_action=<action>   load | push (default: load)
  registry=<url>          Registry URL (default: docker.io/dellhpcomniaaisolution)
  kafkapump_tag=<tag>     kafkapump tag (default: 1.3)
  victoriapump_tag=<tag>  victoriapump tag (default: 1.3)
  telemetry_receiver_tag=<tag>  telemetry_receiver tag (default: 1.3)
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
├── build_images.sh              # Single orchestrator with inline iDRAC builds
├── README.md                    # This file
├── ldms/                        # LDMS aggregator (unique Containerfile)
│   ├── Containerfile.bld_n_run.ubuntu26.04
│   ├── configure.aggregator.sh
│   └── README.md
└── .idrac-telemetry-tools/      # Auto-cloned during build (git repo)
```

## See Also

- `ldms/README.md` — Detailed documentation for LDMS container build
