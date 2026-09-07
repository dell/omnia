# prepare_aarch64_node

Prepares a native ARM64 (aarch64) host for image building over SSH. This is
remote orchestration, not cross-compilation or emulation.

## Architecture

The playbook invokes the role's SSH/data-gathering task files on the OIM and
its `main.yml` directly on the dynamically created `admin_aarch64` host.
No NFS mount is required. Work directories are local to the aarch64 node at
`<OMNIA_DATA_PATH>/image_build_manager`, using the controller's
`OMNIA_DATA_PATH` value. The path defaults to `/opt/omnia/image_build_manager`
and does not honor `IMAGE_BUILD_MANAGER_DATA_PATH`.

### Prerequisites (handled before this role)

- **Validation** — `validate_aarch64_host.yml` (in `validate_build_runtime`) runs on
  localhost: checks IP is configured, pings the host, creates `admin_aarch64` inventory group.
  Fails early if host is unreachable.
- **SSH setup** — `setup_ssh.yml` (in this role) runs on localhost: generates SSH keypair
  if missing, adds host to known_hosts, runs `ssh-copy-id` with credential password,
  verifies passwordless SSH works. Called from a localhost play in the playbook.

### Task files

| File | Runs on | Purpose |
|------|---------|---------|
| `setup_ssh.yml` | localhost | SSH keygen + known_hosts + ssh-copy-id + verify |
| `gather_oim_data.yml` | localhost | Inventory checks + OIM network facts |
| `main.yml` | admin_aarch64 | Node preparation (arch check, dirs, images, regctl, registry) |

### Phases (main.yml)

1. **Architecture validation** — Verifies the remote host is actually aarch64.
2. **OIM hostname resolution** — Adds OIM PXE IP + hostname to `/etc/hosts` on the aarch64 node
   so repo manager (Pulp) is reachable by name.
3. **Local work directories** — Creates the configured image-build tree on the
   aarch64 node (replacing the former NFS mount requirement).
4. **Repo configuration** — Generates `repo_manager.repo` only when a
   `rpm_repos_aarch64` fact is supplied, and copies the Pulp CA certificate
   when configured. The normal setup currently exposes
   `repo_manager_repos_aarch64` instead, so the legacy `.repo` generation is
   skipped in the standard top-level flow.
5. **Builder image pull** — Pulls the builder container image using a two-tier strategy:
   - Try repo manager (Pulp) first: `<oim_ip>:<port>/<image>`
   - Fall back to upstream registry (DockerHub/GHCR) if Pulp fails
6. **regctl installation** — Installs the `regctl` binary on the aarch64 node using a two-tier strategy:
   - Try copying the staged ARM binary from
     `<OMNIA_DATA_PATH>/image_build_manager/aarch64/regctl-linux-arm64` on OIM
   - Fall back to downloading from GitHub releases if copy fails
7. **Registry configuration** — Configures regctl to use HTTP for the local OCI registry.

## Requirements

- SSH access to the aarch64 build host (passwordless or password-based)
- Podman installed on the remote host
- Network connectivity: OIM must reach the aarch64 node (admin NIC or routable path)
- Either the repo manager (Pulp) is accessible from the aarch64 node, or the
  node can access the selected upstream registry (Docker Hub or GHCR)

## Role Variables

See `vars/main.yml` for the full list. Key variables in `image_build_config.yml`:

| Variable | Required | Description |
|----------|----------|-------------|
| `aarch64_inventory_host_ip` | Yes to enable ARM | IPv4 address of the ARM build host; empty disables ARM builds |
| `aarch64_ssh_user` | Yes when enabled | SSH user (shipped value: `root`) |

Key variables in `image_build_credentials.yml`:

| Variable | Required | Description |
|----------|----------|-------------|
| `aarch64_ssh_password` | Yes when enabled | SSH password for initial key setup; current validation requires it even when passwordless SSH already works |

## Orchestration Prerequisites

No dependencies are declared in `meta/main.yml`. The top-level aarch64 build
play runs these stages first:

- `image_build_setup` — environment and config loading
- `collect_build_credentials` — aarch64 SSH credentials
- `validate_build_runtime` — aarch64 host validation and dynamic inventory group creation

## Invocation

```bash
cd src/image_build_manager/playbooks
ansible-playbook image_build_manager.yml --tags build
```

Directly applying this role is insufficient because its dynamic inventory,
controller facts, credentials, and repository data are created by earlier
plays in `build_image_aarch64.yml`.
