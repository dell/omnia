# pxe_buildstream_manager

Manages PXE boot operations with BuildStream integration for compute node provisioning.

## Description

This role orchestrates PXE boot processes integrated with BuildStream Manager (BSM) for large-scale compute node provisioning. It handles effective inventory computation, phone-home verification, GitLab integration, and restart state management.

## Requirements

- PXE-enabled network infrastructure
- BuildStream Manager deployment
- GitLab server for result upload (optional)
- SSH access to cluster nodes

## Role Variables

Available variables are listed below, along with default values (see `vars/main.yml`):

```yaml
# BuildStream Manager configuration
enable_build_stream: false
buildstream_timeout: 3600
phone_home_timeout: 1800

# GitLab integration
gitlab_upload_enabled: false
gitlab_server: ""
gitlab_token: ""

# Inventory and restart management
effective_inventory_path: ""
restart_state_file: ""
```

## Dependencies

None.

## Example Playbook

```yaml
- hosts: localhost
  connection: local
  gather_facts: true
  roles:
    - role: pxe_buildstream_manager
      vars:
        enable_build_stream: true
        buildstream_timeout: 7200
        phone_home_timeout: 2400
```

## Tasks

- `main.yml` - Main orchestration
- `compute_effective_inventory.yml` - Calculate nodes needing restart
- `cloudinit_phone_home.yml` - Handle post-boot phone-home verification
- `upload_to_gitlab.yml` - Upload results to GitLab server
- `update_restart_state.yml` - Update restart state tracking
- `write_node_results.yml` - Write node provisioning results

## License

Apache 2.0

## Author Information

Dell Technologies Omnia Team
