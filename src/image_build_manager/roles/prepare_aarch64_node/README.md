# prepare_aarch64_node

Prepares ARM64 (aarch64) remote build hosts for cross-architecture image building via SSH.

## Architecture

This role runs on the OIM (localhost) and delegates tasks to the aarch64 build host.
No NFS mount is required — all work directories are created locally on the aarch64 node
at `/opt/omnia/image_build_manager`.

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
3. **Local work directories** — Creates `/opt/omnia/image_build_manager/` tree on the aarch64 node
   (replaces the former NFS mount requirement).
4. **Repo configuration** — Generates `repo_manager.repo` from `rpm_repos_aarch64` dict
   and copies the Pulp CA certificate (if configured).
5. **Builder image pull** — Pulls the builder container image using a two-tier strategy:
   - Try repo manager (Pulp) first: `<oim_ip>:<port>/<image>`
   - Fall back to upstream registry (DockerHub/GHCR) if Pulp fails
6. **regctl installation** — Installs the `regctl` binary on the aarch64 node using a two-tier strategy:
   - Try copying from OIM localhost (`/usr/local/bin/regctl`)
   - Fall back to downloading from GitHub releases if copy fails
7. **Registry configuration** — Configures regctl to use HTTP for the local OCI registry.

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
