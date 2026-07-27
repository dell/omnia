# Dataset: Local Storage

## Overview

This dataset configures omnia.sh `--install` to use **local disk storage**
on the OIM host. No NFS server is needed — the omnia shared path is a
plain directory on the local filesystem.

## When to Use

- Simple, single-node deployments
- Flat provisioning setups only
- Environments where NFS is not available or not required

## Limitations

- Does **not** support HA (High Availability) OIM configurations
- Does **not** support multi-node shared storage
- Data is local to the OIM host only

## Prerequisites

1. The directory specified in `omnia_shared_path` must exist on the OIM host
   (it will be created by omnia.sh if it doesn't exist).

## Configuration

Edit `install_config.yml` in this directory:

| Parameter               | Description                                    | Example              |
|-------------------------|------------------------------------------------|----------------------|
| `share_option`          | Must be `"Local"`                              | `"Local"`            |
| `nfs_type`              | Leave empty (not applicable)                   | `""`                 |
| `nfs_server_ip`         | Leave empty (not applicable)                   | `""`                 |
| `nfs_server_share_path` | Leave empty (not applicable)                   | `""`                 |
| `omnia_shared_path`     | Local directory for Omnia shared data          | `"/opt/omnia_shared"` |

## Notes

- NFS-related parameters (`nfs_type`, `nfs_server_ip`, `nfs_server_share_path`)
  are ignored when `share_option` is `"Local"`.
- The test validation will verify that `omnia_shared_path` is set and that the
  directory is accessible after installation.
