# NFS Client Role

## Overview
Configures NFS client mounts on cluster nodes based on their functional roles and host-specific targeting.

## Purpose
- Filters and mounts NFS shares based on node type (Slurm, Kubernetes)
- Configures NFS client packages
- Creates mount points and persistent `/etc/fstab` entries
- Supports bolt-on storage additions
- Supports host-specific mount targeting via PXE mapping

## Key Tasks
- **Load Configuration**: Reads storage and software configuration
- **Build Host Mount Map**: Creates host-to-mount mappings from PXE mapping file (optional)
- **Filter Slurm Mounts**: Identifies NFS shares required for Slurm nodes
- **Filter K8s Mounts**: Identifies NFS shares required for Kubernetes service nodes
- **Process Mounts**: Converts mounts to cloud-init format and adds to functional groups or host-specific map
- **Install NFS Client**: Installs packages, creates mount points, updates `/etc/fstab`, mounts shares

## Mount Targeting Modes

### 1. Functional Group Targeting (Existing)
Mounts are targeted to functional groups using the `functional_group_prefix` field in `storage_config.yml`:

```yaml
mounts:
  - name: slurm_home
    source: "10.0.0.100:/home"
    mount_point: "/home"
    functional_group_prefix: ["slurm", "login"]
    fs_type: nfs4
    mnt_opts: "rw,hard,intr,_netdev"
```

This mount will be added to all functional groups matching the prefixes `slurm*` or `login*`.

### 2. Host-Specific Targeting (New)
Mounts can target specific hosts using the `groups` field and PXE mapping:

```yaml
mounts:
  - name: compute_scratch
    source: "10.0.0.100:/scratch"
    mount_point: "/scratch"
    groups: ["compute", "gpu"]
    fs_type: nfs4
    mnt_opts: "rw,hard,intr,_netdev"
```

When a PXE mapping file is provided, this mount will be added to the `host_mount_map` for all hosts in the specified groups. Cloud-init templates will conditionally render these mounts based on `ds.meta_data.instance_data.local_hostname`.

## Configuration

### Input Files
- `storage_config.yml`: Mount definitions with optional `groups` field for host-specific targeting
- `pxe_mapping_file.csv`: (Optional) CSV file with columns `HOSTNAME` and `PXE_GROUP` for host-specific targeting

### Variables
- `pxe_mapping_file_path`: Path to PXE mapping file (optional, passed to role)

### Output Data Structures
- `cloud_init_groups_dict`: Dictionary mapping functional group names to their mounts and runcmd entries
- `host_mount_map`: Dictionary mapping hostnames to their host-specific mounts and runcmd entries (when PXE mapping provided)

## Cloud-Init Integration

Both functional group and host-specific mounts are rendered in cloud-init templates:

1. **Functional Group Mounts**: Rendered for all nodes in the functional group
2. **Host-Specific Mounts**: Conditionally rendered only for the current node (using `ds.meta_data.instance_data.local_hostname`)

This allows a single cloud-init template to serve multiple nodes while each node receives only its applicable mounts.

