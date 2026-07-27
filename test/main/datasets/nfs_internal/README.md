# Dataset: NFS Internal

## Overview

This dataset configures omnia.sh `--install` to use an **internal NFS server**
— an NFS server running on the OIM host itself. The automation includes
functions to create and configure the NFS server automatically on RHEL.

## When to Use

- Development and testing environments
- Single-node OIM setups where no external NFS is available
- Quick deployments without a separate storage server

## Limitations

- Does **not** support HA (High Availability) OIM configurations
- Does **not** support hierarchical cluster topologies
- The NFS server and OIM share the same host resources

## Prerequisites

1. The OIM host must be running RHEL (or compatible: Rocky, AlmaLinux).
2. The `nfs-utils` package will be installed automatically if missing.
3. Firewall ports for NFS will be opened automatically if `firewalld` is active.

## Configuration

Edit `install_config.yml` in this directory:

| Parameter               | Description                                    | Example             |
|-------------------------|------------------------------------------------|---------------------|
| `share_option`          | Must be `"NFS"`                                | `"NFS"`             |
| `nfs_type`              | Must be `"internal"`                           | `"internal"`        |
| `nfs_server_ip`         | OIM host IP (same machine)                     | `"10.0.0.50"`       |
| `nfs_server_share_path` | Directory to export via NFS                    | `"/exports/omnia"`  |
| `omnia_shared_path`     | Same as `nfs_server_share_path` for internal   | `"/exports/omnia"`  |

## Internal NFS Setup

The test automation will automatically call `setup_internal_nfs_server(host)`
before running `omnia.sh --install`. This function:

1. Installs `nfs-utils` via `dnf`
2. Creates the export directory
3. Adds the export entry to `/etc/exports`
4. Enables and starts the `nfs-server` systemd service
5. Applies `exportfs -rav`
6. Opens firewall ports (if `firewalld` is active)

## Cleanup

After uninstall tests, `cleanup_internal_nfs_server(host)` removes the
export entry and stops the NFS server if no other exports remain.
