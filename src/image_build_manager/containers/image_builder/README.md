# Image Builder Container

Container image used by the `image_build_manager` to build OS images via
[OpenCHAMI image-build](https://github.com/OpenCHAMI/image-build).

## Base Image

`docker.io/library/almalinux:10.0`

## Contents

- **Go** (compiled from source) for building `buildah` and `image-build`
- **Buildah** — OCI image builder (built from source with `btrfs` support)
- **OpenCHAMI image-build** — disk image generator
- **Python 3.12** — for Ansible and helper scripts
- Ansible + boto3 + cryptography (see `requirements.txt`)

## Files

| File | Description |
|------|-------------|
| `Containerfile.el10` | Multi-stage build for EL10 (AlmaLinux 10.0) |
| `requirements.txt` | Python packages installed inside the container |

## Building

The container is built by `containers/build_images.sh` during the
`prepare` phase of the image_build_manager playbook. You do not
normally need to build it manually.

**Manual build** (for development):

```bash
cd src/image_build_manager/containers
podman build -t image-builder:dev -f image_builder/Containerfile.el10 image_builder/
```

## Usage

The playbook launches this container via Podman to execute `image-build`
commands. The container is run with:

- Pulp TLS certificate mounted at `/etc/pki/ca-trust/source/anchors/`
- Build config YAML mounted at `/home/builder/config.yaml`
- Privileged mode for rootless image assembly

See `roles/build_os_images/` for the Ansible tasks that invoke this container.

## License

Apache License, Version 2.0
