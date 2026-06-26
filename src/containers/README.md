# Omnia Container Image Builder

Build Omnia container images for deployment.

## Quick Start

Build the Omnia core container:

```bash
./build_images.sh core core_tag=2.2 omnia_branch=v2.2.0.0
```

The image will be available locally as `omnia_core:2.2`.

---

## Prerequisites

**Podman** must be installed.

Install Podman: [podman.io/getting-started/installation](https://podman.io/getting-started/installation)

*Note: Script supports Podman and Docker build tools (default: Podman)*

---

## Directory Structure

Each container has its own directory with a `build.sh` and a `Containerfile`:

```
src/containers/
├── _common.sh                          # Shared utilities (colors, build function, summary)
├── build_images.sh                     # Wrapper script (CLI, dispatch, summary)
├── README.md                           # This file
├── omnia_core/
│   ├── build.sh                        # build_omnia_core()
│   ├── Containerfile                   # Fedora 42, Python 3.13, Ansible, Go, Git LFS
│   ├── cert-copy.sh
│   ├── entrypoint.sh
│   ├── pyproject.toml
│   └── uv.lock
├── omnia_auth/
│   ├── build.sh                        # build_omnia_auth()
│   └── Containerfile                   # Fedora 42, OpenLDAP
├── omnia_build_stream/
│   ├── build.sh                        # build_omnia_build_stream()
│   ├── Containerfile                   # Fedora 42, FastAPI, uv, s3cmd
│   ├── init_s3cfg.sh
│   ├── pyproject.toml
│   └── uv.lock
├── ldms/
│   ├── build.sh                        # build_ldms()
│   ├── Containerfile.bld_n_run.ubuntu26.04  # Multi-stage: OVIS LDMS builder + runner
│   └── configure.aggregator.sh
├── image_builder/
│   ├── build.sh                        # build_image_builder() (clones OpenCHAMI)
│   ├── Containerfile.el10              # AlmaLinux 10, Buildah, Go, Python
│   └── requirements.txt
├── kafkapump/
│   └── build.sh                        # build_kafkapump() (clones iDRAC Telemetry)
├── victoriapump/
│   └── build.sh                        # build_victoriapump() (clones iDRAC Telemetry)
└── telemetry_receiver/
    └── build.sh                        # build_telemetry_receiver() (clones iDRAC Telemetry)
```

---

## Common Build Commands

### Build Core Container

```bash
# Build with specific Omnia tag (recommended)
./build_images.sh core omnia_branch=v2.2.0.0

# Build with specific Omnia branch and default tag
./build_images.sh core omnia_branch=main

# Build with default settings (uses main branch and core tag 2.2)
./build_images.sh core
```

### Build OIM Group (Core + Auth + Image Builder)

```bash
./build_images.sh oim omnia_branch=v2.2.0.0
```

### Build ALL Containers

```bash
./build_images.sh all omnia_branch=v2.2.0.0
```

### Build Specific Combinations

```bash
# Comma-separated list
./build_images.sh core,auth omnia_branch=v2.2.0.0 core_tag=2.2 auth_tag=1.1

# Build telemetry group
./build_images.sh telemetry

# Build LDMS
./build_images.sh ldms ldms_tag=1.1
```

---

## Available Containers

| Container | CLI Name | Default Tag | Description |
|-----------|----------|-------------|-------------|
| omnia_core | `core` | 2.2 | Core Omnia container (Ansible, Python, SSH) |
| omnia_auth | `auth` | 1.1 | OpenLDAP authentication service |
| omnia_build_stream | `build-stream` | 1.1 | FastAPI build automation service |
| ldms | `ldms` | 1.1 | OVIS LDMS monitoring (multi-stage Ubuntu build) |
| image_builder | `image-builder` | 1.1 | OpenCHAMI image builder (AlmaLinux 10, Buildah) |
| kafkapump | `kafkapump` | 1.3 | iDRAC telemetry → Kafka |
| victoriapump | `victoriapump` | 1.3 | iDRAC telemetry → VictoriaMetrics |
| telemetry_receiver | `telemetry-receiver` | 1.3 | iDRAC telemetry collector |

### Build Groups

| Group | Containers |
|-------|-----------|
| `oim` | core, auth, image-builder (default if no arg) |
| `all` | core, auth, ldms, kafkapump, victoriapump, telemetry-receiver, image-builder |
| `pipeline` | core, auth, ldms, kafkapump, victoriapump, telemetry-receiver, image-builder |
| `telemetry` | kafkapump, victoriapump, telemetry-receiver |

---

## Parameters Reference

### Common (valid for all containers)

| Parameter | Values | Default | Description |
|-----------|--------|---------|-------------|
| `build_tool` | `podman`, `docker` | `podman` | Container build tool |
| `build_action` | `load`, `push` | `load` | Load locally or push to registry |

### Container-specific tags

| Parameter | Default | Container |
|-----------|---------|-----------|
| `core_tag` | `2.2` | omnia_core |
| `auth_tag` | `1.1` | omnia_auth |
| `build_stream_tag` | `1.1` | omnia_build_stream |
| `ldms_tag` | `1.1` | ldms |
| `image_builder_tag` | `1.1` | image_builder |
| `kafkapump_tag` | `1.3` | kafkapump |
| `victoriapump_tag` | `1.3` | victoriapump |
| `telemetry_receiver_tag` | `1.3` | telemetry_receiver |
| `omnia_branch` | `main` | omnia_core (branch/tag to clone) |

### Push to Registry

```bash
# Requires Docker (Podman push not supported via this script)
./build_images.sh core core_tag=2.2 omnia_branch=v2.2.0.0 build_tool=docker build_action=push
```

---

## Parameter Validation

The script validates parameters and shows context-specific errors:

```bash
# Invalid parameter
./build_images.sh core invalid_param=value
# Error: Invalid parameter(s): invalid_param
# Valid parameters for 'core': build_tool build_action core_tag omnia_branch

# Wrong container-specific parameter
./build_images.sh core auth_tag=1.0
# Error: Parameter 'auth_tag' is not valid for container 'core'
```

---

## Docker vs Podman

**Podman (default):**
- No daemon required
- Rootless by default

**Docker:**
- Required for `build_action=push`
- Requires buildx for multi-platform builds

### Docker Setup

```bash
sudo systemctl start docker
sudo systemctl enable docker
docker buildx create --name mybuilder --driver docker-container --use
docker buildx inspect --bootstrap
```

---

## Updating Python Packages

For containers using uv (omnia_core, omnia_build_stream):

1. **Install uv**: `pip install uv`
2. **Update pyproject.toml**: Navigate to the container folder and update
3. **Update the lock file**: Run `uv lock` from the same directory

---

## Troubleshooting

**Issue:** Warning about default branch
```
⚠️ Warning: omnia_branch not specified, using default branch: main
```
**Solution:** Always specify `omnia_branch` for production builds.

**Issue:** Build fails
**Solution:** Ensure Podman/Docker is running and you have internet access to pull base images.

**Issue:** Permission errors with Podman
**Solution:** Run as non-root user or configure subuid/subgid mappings.

---

## Support

For issues or questions, refer to the [Omnia documentation](https://omnia.readthedocs.io/en/latest/).
