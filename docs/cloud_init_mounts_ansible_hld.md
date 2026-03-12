# High-Level Design: Cloud-Init Mounts Configuration

## Overview

This document describes a flexible, cloud-init compatible mount and swap configuration system that manages storage mounts and swap files with fine-grained control over which nodes receive each configuration.

## Design Goals

1. **Cloud-Init Compatibility**: Generate configurations compatible with cloud-init's mounts module
2. **Granular Control**: Target specific nodes by roles, hostnames, or groups from pxe_mapping.csv
3. **Idempotency**: Support repeated executions without side effects
4. **Flexibility**: Support multiple mounts and swap configurations per host
5. **Directory**: directory creation is automatic, no need to specify it in the configuration, only setting permissions would be in runcmd

## Architecture

### 1. Configuration Input Structure

The system accepts configuration from `storage_config.yml`:

#### 1.1 Mounts Configuration

TODO: fs_ prefix to be retained? its cloud-init specific
```yaml
mounts:
  - name: "nfs_slurm_home"              # Unique identifier
    fs_spec: "172.16.107.168:/mnt/share/omnia"
    fs_file: "/home"
    fs_vfstype: "nfs"
    fs_mntops: "defaults,nofail,_netdev"
    fs_freq: "0"
    fs_passno: "0"
    roles: ["slurm_control_node", "slurm_node"]
    hostnames: []
    groups: []
```

**Supported Filesystem Types (`fs_vfstype`):**

- **Network Filesystems:**
  - `nfs` - Network File System (NFS v3/v4)
  - `nfs4` - NFS version 4 explicitly
  - `cifs` - Common Internet File System (SMB/Windows shares)
  - `beegfs` - BeeGFS parallel filesystem
  - `glusterfs` - GlusterFS distributed filesystem
  - `lustre` - Lustre parallel distributed filesystem

- **Local Filesystems:**
  - `ext4` - Fourth Extended Filesystem (recommended for Linux)
  - `ext3` - Third Extended Filesystem
  - `xfs` - XFS filesystem
  - `btrfs` - B-tree filesystem
  - `vfat` - FAT32 filesystem
  - `ntfs` - NTFS filesystem (requires ntfs-3g)

- **Special Filesystems:**
  - `tmpfs` - Temporary filesystem in RAM
  - `auto` - Auto-detect filesystem type (default)

#### 1.2 Swap Configuration

```yaml
swap:
  - name: "compute_swap"
    filename: "/swapfile"
    size: "4G"
    maxsize: "8G"
    roles: ["slurm_node"]
    hostnames: []
    groups: []
```

#### 1.3 Mount Default Fields

```yaml
mount_default_fields:
  fields: ["auto", "defaults,nofail,x-systemd.after=cloud-init-network.service", "0", "2"]
  roles: []
  hostnames: []
  groups: []
```

### 2. Resolution Process

```
┌─────────────────────────────────────────────────────────────┐
│  1. Parse PXE Mapping                                       │
│     - Build hostname → (role, group, ip, mac) mapping       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  2. Resolve Mount Defaults for Each Host                    │
│     - Check if hostname matches mount_default_fields        │
│       roles/hostnames/groups                                │
│     - Return applicable defaults or global defaults         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  3. Filter Mounts for Each Host                             │
│     - For each mount:                                       │
│       - If roles/hostnames/groups empty
│       - Else check if hostname matches criteria             │
│     - Return list of applicable mounts per host             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  4. Filter Swap for Each Host                               │
│     - Apply same filtering logic as mounts                  │
│     - Validate: max 1 swap for cloud-init mode              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  5. Generate Cloud-Init Configuration                       │
│     - Generate per-host cloud-init YAML                     │
│     - Append to the cloud init yml instance wise per host   │
│     TODO: Need to check if this is instance wise is [possible or not]
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  6. Apply Configuration                                     │
│     - This will applied in the order cloud-init executes    │
│       its modules when PXE booted                           │
└─────────────────────────────────────────────────────────────┘
```

### 3. PXE Mapping File

The `pxe_mapping_file.csv` is the source of truth for node attributes:

```csv
FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,PARENT_SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP
slurm_control_node,grp0,SVC001,PARENT001,manager01,aa:bb:cc:dd:ee:01,192.168.1.10,aa:bb:cc:dd:ee:f1,192.168.2.10
slurm_node,grp1,SVC002,PARENT001,compute01,aa:bb:cc:dd:ee:02,192.168.1.11,aa:bb:cc:dd:ee:f2,192.168.2.11
slurm_node,grp1,SVC003,PARENT001,compute02,aa:bb:cc:dd:ee:03,192.168.1.12,aa:bb:cc:dd:ee:f3,192.168.2.12
slurm_node,grp2,SVC004,PARENT001,compute03,aa:bb:cc:dd:ee:04,192.168.1.13,aa:bb:cc:dd:ee:f4,192.168.2.13
```

**Key Fields:**
- `FUNCTIONAL_GROUP_NAME`: Node role (e.g., slurm_control_node, slurm_node)
- `GROUP_NAME`: Node group for targeting
- `HOSTNAME`: Unique hostname for the node
- `ADMIN_MAC` / `ADMIN_IP`: Admin network interface details

### 4. Data Flow Example

#### Input Configuration

```yaml
# storage_config.yml
mounts:
  - name: "nfs_slurm_home"
    fs_spec: "172.16.107.168:/mnt/share/omnia"
    fs_file: "/home"
    fs_vfstype: "nfs"
    fs_mntops: "defaults,nofail,_netdev"
    roles: ["slurm_control_node", "slurm_node"]

swap:
  - name: "compute_swap"
    filename: "/swapfile"
    size: "4G"
    roles: ["slurm_node"]

mount_default_fields:
  fields: ["auto", "defaults,nofail,x-systemd.after=cloud-init-network.service", "0", "2"]
  roles: []
```

#### Resolution for compute01

Given PXE mapping shows: `compute01` has `role=slurm_node`, `group=grp1`

**Applicable Configuration:**
- Mount: `nfs_slurm_home` (matches role `slurm_node`)
- Swap: `compute_swap` (matches role `slurm_node`)

#### Generated Cloud-Init for compute01

```yaml
#cloud-config
# Hostname: compute01

mounts:
  - ["172.16.107.168:/mnt/share/omnia", "/home", "nfs", "defaults,nofail,_netdev", "0", "0"]

mount_default_fields: ["auto", "defaults,nofail,x-systemd.after=cloud-init-network.service", "0", "2"]

swap:
  filename: /swapfile
  size: 4G
```

### 5. Validation Requirements

#### Level 1: Schema Validation (JSON Schema)
- ✅ Data types and formats
- ✅ Required fields (name, fs_spec, fs_file for mounts; name, filename, size for swap)
- ✅ Path patterns (absolute paths starting with `/`)
- ✅ Size format (auto, 4G, 512M, etc.)
- ✅ Filesystem types (enum of supported types)
- ✅ Unique items in arrays

#### Level 2: Business Logic Validation
- **Unique mount names** across all mounts
- **Unique swap names** across all swaps
- **Hostname existence** in PXE mapping
- **Swap filename uniqueness** per host
- **Max 1 swap** per host for cloud-init mode
- **Mount point uniqueness** per host
- **No circular dependencies** (e.g., swap on tmpfs)

#### JSON Schema

The configuration is validated using JSON Schema located at:
`/new_omnia/omnia/ansible_collections/dell/storage_generic/common/library/module_utils/input_validation/schema/storage_config.json`

**Key Schema Validations for Mounts:**
```json
{
  "mounts": {
    "type": "array",
    "items": {
      "properties": {
        "name": {
          "type": "string",
          "pattern": "^[a-zA-Z0-9_-]+$",
          "minLength": 1,
          "maxLength": 64
        },
        "fs_spec": {
          "type": "string",
          "minLength": 1
        },
        "fs_file": {
          "type": "string",
          "pattern": "^/[a-zA-Z0-9/_.-]*$"
        },
        "fs_vfstype": {
          "type": "string",
          "enum": ["auto", "ext2", "ext3", "ext4", "xfs", "btrfs", 
                   "nfs", "nfs4", "cifs", "tmpfs", "cephfs", "vfat", "ntfs"]
        },
        "fs_mntops": {
          "type": "string",
          "pattern": "^[a-zA-Z0-9,=._-]+$"
        },
        "fs_freq": {
          "type": "string",
          "pattern": "^[0-2]$"
        },
        "fs_passno": {
          "type": "string",
          "pattern": "^[0-9]$"
        },
        "roles": {
          "type": "array",
          "items": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
          "uniqueItems": true
        },
        "hostnames": {
          "type": "array",
          "items": {"type": "string", "pattern": "^[a-zA-Z0-9.-]+$"},
          "uniqueItems": true
        },
        "groups": {
          "type": "array",
          "items": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
          "uniqueItems": true
        }
      },
      "required": ["name", "fs_spec", "fs_file"]
    }
  }
}
```

**Key Schema Validations for Swap:**
```json
{
  "swap": {
    "type": "array",
    "items": {
      "properties": {
        "name": {
          "type": "string",
          "pattern": "^[a-zA-Z0-9_-]+$",
          "minLength": 1,
          "maxLength": 64
        },
        "filename": {
          "type": "string",
          "pattern": "^/[a-zA-Z0-9/_.-]+$"
        },
        "size": {
          "type": "string",
          "pattern": "^(auto|[0-9]+[BKMGT]?)$"
        },
        "maxsize": {
          "type": "string",
          "pattern": "^[0-9]+[BKMGT]?$"
        },
        "roles": {
          "type": "array",
          "items": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
          "uniqueItems": true
        },
        "hostnames": {
          "type": "array",
          "items": {"type": "string", "pattern": "^[a-zA-Z0-9.-]+$"},
          "uniqueItems": true
        },
        "groups": {
          "type": "array",
          "items": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
          "uniqueItems": true
        }
      },
      "required": ["name", "filename", "size"]
    }
  }
}
```

**Key Schema Validations for Mount Default Fields:**
```json
{
  "mount_default_fields": {
    "type": "object",
    "properties": {
      "fields": {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 6,
        "maxItems": 6
      },
      "roles": {
        "type": "array",
        "items": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
        "uniqueItems": true
      },
      "hostnames": {
        "type": "array",
        "items": {"type": "string", "pattern": "^[a-zA-Z0-9.-]+$"},
        "uniqueItems": true
      },
      "groups": {
        "type": "array",
        "items": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
        "uniqueItems": true
      }
    },
    "required": ["fields"]
  }
}
```

### 6. Key Design Decisions

1. **PXE Mapping as Source of Truth**
   - All hostname, role, and group data from `pxe_mapping_file.csv`
   - Single source for node attributes

2. **Mount Default Fields with Targeting**
   - Supports roles, hostnames, groups
   - Allows different defaults for different node types
   - Falls back to global defaults

3. **Cloud-Init Constraint**
   - Max 1 swap file per host (cloud-init limitation)
   - Multiple mounts supported per host

4. **Targeting Logic**
   - Empty roles/hostnames/groups = apply to all hosts
   - Union of all specified criteria
   - Unique hostname list per mount/swap

5. **Idempotency**
   - Cloud-init configurations are idempotent by design
   - Repeated executions produce same result

## Conclusion

This design provides a flexible, cloud-init compatible mount and swap configuration system with granular per-host control through roles, hostnames, and groups targeting. The system resolves configurations from `storage_config.yml` and `pxe_mapping_file.csv` to generate instance-specific cloud-init configurations that are applied on each target node.
