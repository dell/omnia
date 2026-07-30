# Dataset: NFS External

## Overview

This dataset configures omnia.sh `--install` to use an **external NFS server**
— an NFS server that is separate from the OIM host and already provisioned by
the user.

## When to Use

- Production deployments with shared storage
- Multi-node clusters requiring a common omnia shared path
- Environments where an external NFS server is already available

## Prerequisites

1. An NFS server must be running and accessible from the OIM host.
2. The NFS export path must be configured and exported on the NFS server.
3. The OIM host must have the NFS share mounted at `omnia_shared_path`.

## Configuration

Edit `install_config.yml` in this directory:

| Parameter               | Description                                    | Example             |
|-------------------------|------------------------------------------------|---------------------|
| `share_option`          | Must be `"NFS"`                                | `"NFS"`             |
| `nfs_type`              | Must be `"external"`                           | `"external"`        |
| `nfs_server_ip`         | IP address of the NFS server                   | `"10.0.0.100"`      |
| `nfs_server_share_path` | Exported path on the NFS server                | `"/exports/omnia"`  |
| `omnia_shared_path`     | Mount point on OIM where NFS share is mounted  | `"/opt/omnia_shared"` |

## Validation

This is the **default dataset** for sanity tests. When `dataset: nfs_external`
is set in `test_config.yml`, the sanity test suite will:

1. Validate all required parameters are present
2. Run `omnia.sh --install` with these values
3. Verify the container, services, and metadata are created correctly
