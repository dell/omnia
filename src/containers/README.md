# Omnia Container Images

Container build infrastructure for all Omnia container images.
Each container has its own subdirectory with a `build.sh` and `Containerfile`.

## Quick Start

```bash
# Build OIM group (core + auth + image-builder) — default
./build_images.sh oim

# Build a single container with custom tag
./build_images.sh core core_tag=2.2

# Build all containers
./build_images.sh all
```

**Prerequisite:** Podman (default) or Docker must be installed.

---

## Directory Layout

```
src/containers/
├── build_images.sh          # Entry point — CLI dispatch + build summary
├── _common.sh               # Shared helpers: colors, container_build(), print_build_summary()
├── README.md
│
├── omnia_core/              # Core Omnia container
│   ├── build.sh             #   build_omnia_core()
│   ├── Containerfile        #   Fedora 42 · Python 3.13 · Ansible · Go · Git LFS
│   ├── cert-copy.sh
│   ├── entrypoint.sh
│   ├── pyproject.toml
│   └── uv.lock
│
├── omnia_auth/              # OpenLDAP authentication
│   ├── build.sh             #   build_omnia_auth()
│   └── Containerfile        #   Fedora 42 · OpenLDAP
│
├── omnia_build_stream/      # BuildStream API service
│   ├── build.sh             #   build_omnia_build_stream()
│   ├── Containerfile        #   Fedora 42 · FastAPI · uv · s3cmd
│   ├── init_s3cfg.sh
│   ├── pyproject.toml
│   └── uv.lock
│
├── image_builder/           # OS image builder (OpenCHAMI) — x86_64 + aarch64
│   ├── build.sh             #   build_image_builder()  → auto-detects arch
│   ├── Containerfile.el10   #   AlmaLinux 10 · Buildah · Go · Python
│   └── requirements.txt
│
├── ldms/                    # OVIS LDMS telemetry sampler
│   ├── build.sh             #   build_ldms()
│   ├── Containerfile.bld_n_run.ubuntu26.04  # Multi-stage build
│   └── configure.aggregator.sh
│
├── kafkapump/               # iDRAC telemetry → Kafka
│   └── build.sh             #   build_kafkapump()
│
├── victoriapump/            # iDRAC telemetry → VictoriaMetrics
│   └── build.sh             #   build_victoriapump()
│
└── telemetry_receiver/      # iDRAC telemetry collector
    └── build.sh             #   build_telemetry_receiver()
```

---

## Containers

| Container | CLI Name | Default Tag | Base | Description |
|-----------|----------|-------------|------|-------------|
| omnia_core | `core` | 2.2 | Fedora 42 | Core container — Ansible, Python 3.13, SSH, Go, Git LFS |
| omnia_auth | `auth` | 1.1 | Fedora 42 | OpenLDAP authentication service |
| omnia_build_stream | `build-stream` | 1.1 | Fedora 42 | FastAPI build automation + S3 integration |
| image_builder | `image-builder` | 1.1 | AlmaLinux 10 | OpenCHAMI image builder — Buildah, Go, Python |
| ldms | `ldms` | 1.1 | Ubuntu 26.04 | OVIS LDMS monitoring (multi-stage build) |
| kafkapump | `kafkapump` | 1.3 | — | iDRAC telemetry → Kafka bridge |
| victoriapump | `victoriapump` | 1.3 | — | iDRAC telemetry → VictoriaMetrics bridge |
| telemetry_receiver | `telemetry-receiver` | 1.3 | — | iDRAC telemetry collector |

### Build Groups

| Group | Containers | Use Case |
|-------|-----------|----------|
| `oim` | core, auth, image-builder | OIM deployment (default) |
| `all` | All 8 containers | Full rebuild |
| `pipeline` | core, auth, ldms, kafkapump, victoriapump, telemetry-receiver, image-builder | CI/CD pipeline |
| `telemetry` | kafkapump, victoriapump, telemetry-receiver | Telemetry stack only |

---

## Architecture Support (x86_64 / aarch64)

### Image Builder — Dual Architecture

The `image_builder` container automatically detects the host architecture and produces
the correct image name:

| Host Arch | Image Name | Platform |
|-----------|-----------|----------|
| x86_64 | `image-build-el10` | `linux/amd64` |
| aarch64 | `image-build-aarch64` | `linux/arm64` |

The `Containerfile.el10` is multi-arch — it downloads the correct Go toolchain
for the detected architecture. No separate Containerfile is needed.

```bash
# On x86_64 host → produces image-build-el10:1.1
./build_images.sh image-builder

# On aarch64 host → produces image-build-aarch64:1.1
./build_images.sh image-builder

# With Docker — uses docker info to detect platform
./build_images.sh image-builder build_tool=docker
```

### Other Containers

- **omnia_core** — x86_64 only (Fedora 42 base)
- **ldms** — architecture set by `--arch` in build script
- **RPM build** — see `src/rpm_build/README.md` for LDMS RPM builds on both architectures

---

## Build Commands

```bash
# Single container
./build_images.sh core core_tag=2.2

# Comma-separated list
./build_images.sh core,auth core_tag=2.2 auth_tag=1.1

# Telemetry group
./build_images.sh telemetry

# Push to registry (requires Docker)
./build_images.sh core core_tag=2.2 build_tool=docker build_action=push
```

---

## Parameters

### Global

| Parameter | Values | Default | Description |
|-----------|--------|---------|-------------|
| `build_tool` | `podman`, `docker` | `podman` | Container build tool |
| `build_action` | `load`, `push` | `load` | Load locally or push to registry |

### Per-Container Tags

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

Parameter validation is built in — the script rejects unknown or mismatched parameters.

---

## Docker vs Podman

| Feature | Podman (default) | Docker |
|---------|-----------------|--------|
| Daemon | Not required | Required |
| Rootless | Default | Requires config |
| Push to registry | Not supported via script | Supported (`build_action=push`) |
| Multi-platform | Via `--arch` flag | Via `buildx` |

```bash
# Docker setup (if needed)
sudo systemctl start docker
docker buildx create --name mybuilder --driver docker-container --use
docker buildx inspect --bootstrap
```

---

## Updating Python Dependencies

For containers using **uv** (omnia_core, omnia_build_stream):

1. Install uv: `pip install uv`
2. Edit `pyproject.toml` in the container directory
3. Run `uv lock` to regenerate the lock file

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| Build fails | Verify Podman/Docker is running and internet is accessible |
| Permission errors (Podman) | Run as non-root; configure subuid/subgid if needed |
| Image-builder wrong arch | Check `uname -m`; use `build_tool=docker` for cross-platform |