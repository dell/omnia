# Image Builder Container

Container image used by the `image_build_manager` to build OS images via
[OpenCHAMI image-builder](https://github.com/OpenCHAMI/image-builder).

## Base Image

`docker.io/library/almalinux:10.0`

## Contents

- **Go toolchain** — downloaded for compiling Buildah
- **Buildah** — OCI image builder (built from source with `btrfs` support)
- **OpenCHAMI image-builder** — Python disk-image generator
- **Python 3.12** — for Ansible and helper scripts
- Ansible + boto3 + cryptography (see `requirements.txt`)

## Files

| File | Description |
|------|-------------|
| `Containerfile.el10` | Multi-stage build for EL10 (AlmaLinux 10.0) |
| `requirements.txt` | Python packages installed inside the container |

## Building

The runtime playbooks do not build this image during `prepare`. They pull the
published image from the repository manager first and then its configured
upstream registry. `containers/build_images.sh` is a developer utility for
building and publishing the image sources.

**Development build** (requires network access to clone OpenCHAMI sources):

```bash
cd src/image_build_manager/containers
./build_images.sh
```

The Containerfile's build context must contain the cloned OpenCHAMI
`image-builder` `src/` tree, so invoking `podman build` directly against the
checked-in `image_builder/` directory is insufficient.

## Usage

When `image_build_type: "image-builder"` is selected, the playbook launches
the architecture-specific image via Podman to execute `image-build` commands.
The `image-thrillhouse` engine uses a different upstream image. The
image-builder container is run with:

- Pulp TLS certificate mounted at `/etc/pki/ca-trust/source/anchors/` when configured
- Build config YAML mounted at `/home/builder/config.yaml`
- root user and privileged container access for image assembly

See `roles/build_os_images/` for the Ansible tasks that invoke this container.

## License

Apache License, Version 2.0
