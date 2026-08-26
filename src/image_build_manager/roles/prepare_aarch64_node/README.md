# prepare_aarch64_node

Prepares ARM64 (aarch64) remote build hosts for cross-architecture image building via SSH.

## Architecture

This role runs on the OIM (localhost) and delegates tasks to the aarch64 build host.
No NFS mount is required — all work directories are created locally on the aarch64 node
at `/opt/omnia/image_build_manager`.

### Phases

1. **SSH connectivity** — Adds host to known_hosts, sets up passwordless SSH via `ssh-copy-id`
   if not already configured (uses `aarch64_ssh_password` from credentials).
2. **Architecture validation** — Verifies the remote host is actually aarch64.
3. **OIM hostname resolution** — Adds OIM PXE IP + hostname to `/etc/hosts` on the aarch64 node
   so repo manager (Pulp) is reachable by name.
4. **Local work directories** — Creates `/opt/omnia/image_build_manager/` tree on the aarch64 node
   (replaces the former NFS mount requirement).
5. **Repo configuration** — Generates `repo_manager.repo` from `rpm_repos_aarch64` dict
   and copies the Pulp CA certificate (if configured).
6. **Builder image pull** — Pulls the builder container image using a two-tier strategy:
   - Try repo manager (Pulp) first: `<oim_ip>:<port>/<image>`
   - Fall back to upstream registry (DockerHub/GHCR) if Pulp fails
7. **regctl installation** — Installs the `regctl` binary on the aarch64 node using a two-tier strategy:
   - Try copying from OIM localhost (`/usr/local/bin/regctl`)
   - Fall back to downloading from GitHub releases if copy fails
8. **Registry configuration** — Configures regctl to use HTTP for the local OCI registry.

## Requirements

- SSH access to the aarch64 build host (passwordless or password-based)
- Podman installed on the remote host
- Network connectivity: OIM must reach the aarch64 node (admin NIC or routable path)
- Either: repo manager (Pulp) accessible from aarch64 node, OR internet access for DockerHub fallback

## Role Variables

See `vars/main.yml` for the full list. Key variables in `image_build_config.yml`:

| Variable | Required | Description |
|----------|----------|-------------|
| `aarch64_inventory_host_ip` | Yes | IPv4 address of the ARM build host |
| `aarch64_ssh_user` | Yes | SSH user (default: `root`) |

Key variables in `image_build_credentials.yml`:

| Variable | Required | Description |
|----------|----------|-------------|
| `aarch64_ssh_password` | Yes* | SSH password for initial key setup (*not needed if passwordless SSH is pre-configured) |

## Dependencies

- `image_build_setup` — environment and config loading
- `collect_build_credentials` — aarch64 SSH credentials
- `validate_build_runtime` — aarch64 host validation and dynamic inventory group creation

## Example

```yaml
- hosts: admin_aarch64
  gather_facts: false
  roles:
    - prepare_aarch64_node
```
