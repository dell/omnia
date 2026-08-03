# image_build_setup

Setup role that runs first (tag: `always`). Loads configuration, validates
environment, checks prerequisites, parses `repo_status.yml` via the
`parse_repo_status` Python module, and sets up project directories.

## What It Does

1. Loads `image_build_config.yml` from input project directory
2. Validates environment variables (`SYSTEM_ADMIN_NIC_IPV4`, etc.)
3. Validates prerequisites (dual-mode stat checks):
   - `repo_status.yml` — always required
   - `package_groups.yml` — when `functional_groups_source: "config"`
   - `CATALOG_FILE_PATH` env var — when `functional_groups_source: "catalog"`
4. Parses `repo_status.yml` via `omnia.image_build.parse_repo_status` module
5. Sets OS facts (`cluster_os_type`, `cluster_os_version`, `repo_port`)
6. Builds per-architecture repo lists (`repo_manager_repos_x86_64`, `repo_manager_repos_aarch64`)
7. Validates repo manager certificate (from `repo_manager.certificates.server_crt` in `repo_status.yml`)
8. Sets S3 endpoint facts

## Requirements

- Valid `omnia.env` sourced (system environment variables)
- Python 3.12+, Ansible 2.20+

## Modules Used

| Module | Purpose |
|--------|---------|
| `parse_repo_status` | Parses `repo_status.yml`, extracts OS version, repo port, and builds per-arch repo lists |

## Role Variables

See `defaults/main.yml` and `vars/main.yml` for the full list.

## Dependencies

None (this is the first role to run).

## Example

```yaml
- hosts: localhost
  roles:
    - image_build_setup
```
