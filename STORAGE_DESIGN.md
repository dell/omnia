# Storage Configuration Design

**Version:** 1.0  
**Date:** 2026-03-20  
**Status:** Design Complete

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Configuration Schema](#configuration-schema)
4. [Mount Default Fields (Profiles)](#mount-default-fields-profiles)
5. [Storage Technologies](#storage-technologies)
6. [Usage Examples](#usage-examples)
7. [Priority Resolution](#priority-resolution)
8. [Best Practices](#best-practices)
9. [Validation Rules](#validation-rules)

---

## Overview

This design provides a flexible, profile-based mount configuration system for Dell storage solutions in HPC environments. It supports:

- **VAST NFS Storage** - High-performance NFS storage for shared filesystems
- **PowerVault iSCSI Storage** - Block storage for persistent data and databases
- **Generic Network Storage** - NFS, CIFS, and other network filesystems
- **Local Storage** - Direct-attached storage and local disks

### Key Features

- ✅ **Profile-based configuration** - Reusable templates for common mount patterns
- ✅ **Priority-based resolution** - Explicit values override profile defaults
- ✅ **Vendor-specific optimizations** - VAST and PowerVault tuned profiles
- ✅ **Role-based targeting** - Mount configurations per node role
- ✅ **Validation enforcement** - Schema validation ensures correct configuration

---

## Architecture

### Configuration Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     storage_config.yml                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  mount_default_fields (Profiles)                       │   │
│  │  ├─ vast_nfs                                           │   │
│  │  ├─ vast_nfs_performance                               │   │
│  │  ├─ powervault_iscsi                                   │   │
│  │  ├─ network_storage                                    │   │
│  │  └─ bind_mounts                                        │   │
│  └────────────────────────────────────────────────────────┘   │
│                           ▼                                     │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  mounts (Mount Entries)                                │   │
│  │  ├─ vast_home (uses vast_nfs profile)                 │   │
│  │  ├─ powervault_persist (uses powervault_iscsi)        │   │
│  │  └─ powervault_mysql_bind (uses bind_mounts)          │   │
│  └────────────────────────────────────────────────────────┘   │
│                           ▼                                     │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  powervault_config (Optional)                          │   │
│  │  ├─ ip: [controller IPs]                              │   │
│  │  ├─ iscsi_initiator: IQN                              │   │
│  │  └─ volume_id: WWN                                    │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                           ▼
        ┌──────────────────────────────────────┐
        │   Schema Validation                  │
        │   (storage_config.json)              │
        └──────────────────────────────────────┘
                           ▼
        ┌──────────────────────────────────────┐
        │   Cloud-Init Generation              │
        │   (Jinja2 Templates)                 │
        └──────────────────────────────────────┘
                           ▼
        ┌──────────────────────────────────────┐
        │   Node Provisioning                  │
        │   (Per Role)                         │
        └──────────────────────────────────────┘
```

---

## Configuration Schema

### File Structure

```yaml
# storage_config.yml

# PowerVault iSCSI configuration (optional)
powervault_config:
  ip: [list of controller IPs]
  port: 3260
  iscsi_initiator: "iqn.2025-01.com.dell:hostname"
  volume_id: "00c0ff4343f1f1f1001c8c4e6901000000"

# Mount default profiles (templates)
mount_default_fields:
  profile_name:
    fs_type: "filesystem_type"
    mnt_opts: "mount_options"
    dump_freq: "0"
    fsck_pass: "0"

# Mount entries
mounts:
  - name: "unique_mount_name"
    source: "device_or_network_path"
    mount_point: "/mount/path"
    mount_default_field: "profile_name"  # Optional
    fs_type: "filesystem_type"           # Optional (overrides profile)
    mnt_opts: "mount_options"            # Optional (overrides profile)
    dump_freq: "0"                       # Optional (overrides profile)
    fsck_pass: "0"                       # Optional (overrides profile)
    roles: ["role1", "role2"]            # Required

# Swap configuration (optional)
swap:
  - name: "swap_name"
    filename: "/swapfile"
    size: "4G"
    roles: ["role1"]
```

---

## Mount Default Fields (Profiles)

Profiles are reusable templates that provide default values for mount configurations. They define the "HOW to mount" (technical settings), while mount entries define the "WHAT/WHERE/WHOM" (targeting and specifics).

### Profile Structure

```yaml
mount_default_fields:
  profile_name:
    fs_type: "filesystem_type"      # Required
    mnt_opts: "mount_options"       # Required
    dump_freq: "0"                  # Required (usually "0")
    fsck_pass: "0"                  # Required (usually "0" or "2")
```

### Standard Profiles

#### 1. `default` - Standard NFS Defaults

```yaml
default:
  fs_type: "nfs"
  mnt_opts: "defaults,nofail,_netdev,x-systemd.after=cloud-init-network.service"
  dump_freq: "0"
  fsck_pass: "0"
```

**Use Case:** Generic NFS mounts with standard options

---

#### 2. `vast_nfs` - VAST NFS Standard Configuration

```yaml
vast_nfs:
  fs_type: "nfs4"
  mnt_opts: "defaults,nofail,_netdev,noatime,x-systemd.after=cloud-init-network.service"
  dump_freq: "0"
  fsck_pass: "0"
```

**Use Case:** VAST Data NFS exports with standard performance  
**Features:**
- NFSv4 protocol
- `noatime` for improved performance
- Network dependency handling

---

#### 3. `vast_nfs_performance` - VAST NFS High-Performance

```yaml
vast_nfs_performance:
  fs_type: "nfs4"
  mnt_opts: "defaults,nofail,_netdev,noatime,nodiratime,rsize=1048576,wsize=1048576"
  dump_freq: "0"
  fsck_pass: "0"
```

**Use Case:** VAST Data NFS for high-throughput workloads (scratch, datasets)  
**Features:**
- NFSv4 protocol
- **1MB read/write buffers** (`rsize=1048576,wsize=1048576`)
- `noatime` and `nodiratime` for maximum performance
- Optimized for large sequential I/O

---

#### 4. `powervault_iscsi` - PowerVault iSCSI Block Storage

```yaml
powervault_iscsi:
  fs_type: "xfs"
  mnt_opts: "defaults,_netdev,noatime,x-systemd.requires=iscsi.service"
  dump_freq: "0"
  fsck_pass: "0"
```

**Use Case:** PowerVault iSCSI persistent storage  
**Features:**
- XFS filesystem (high performance, scalability)
- Requires iSCSI service to be running
- `noatime` for improved performance
- Network device handling

**Note:** Matches `setup_iscsi_storage.sh` default configuration

---

#### 5. `network_storage` - Generic Network Storage

```yaml
network_storage:
  fs_type: "auto"
  mnt_opts: "defaults,nofail,_netdev,x-systemd.after=cloud-init-network.service"
  dump_freq: "0"
  fsck_pass: "0"
```

**Use Case:** Generic network filesystems (NFS, CIFS, etc.)

---

#### 6. `local_storage` - Local Disk Storage

```yaml
local_storage:
  fs_type: "auto"
  mnt_opts: "defaults,nofail,noatime"
  dump_freq: "0"
  fsck_pass: "2"
```

**Use Case:** Local disks (ext4, xfs, etc.)  
**Note:** `fsck_pass: "2"` enables filesystem check

---

#### 7. `bind_mounts` - Bind Mounts

```yaml
bind_mounts:
  fs_type: "none"
  mnt_opts: "bind"
  dump_freq: "0"
  fsck_pass: "0"
```

**Use Case:** Bind mounts (e.g., `/mnt/slurm-persist/mysql` → `/var/lib/mysql`)

---

#### 8. `scratch_storage` - High-Performance Scratch

```yaml
scratch_storage:
  fs_type: "xfs"
  mnt_opts: "defaults,nofail,noatime,nodiratime,largeio,inode64"
  dump_freq: "0"
  fsck_pass: "2"
```

**Use Case:** Local high-performance scratch storage

---

#### 9. `global` - Global Fallback

```yaml
global:
  fs_type: "auto"
  mnt_opts: "defaults,nofail,x-systemd.after=cloud-init-network.service"
  dump_freq: "0"
  fsck_pass: "2"
```

**Use Case:** Fallback when no specific profile matches

---

## Storage Technologies

### VAST NFS Storage

**Overview:** VAST Data provides high-performance, scale-out NFS storage optimized for HPC workloads.

#### Configuration Format

```yaml
mounts:
  - name: "vast_home"
    source: "192.168.1.100:/home"  # VAST NFS export
    mount_point: "/home"
    mount_default_field: "vast_nfs"
    roles: ["slurm_control_node", "slurm_node", "login_node"]
```

#### Source Format

- **Pattern:** `<VAST_IP>:<export_path>`
- **Example:** `192.168.1.100:/home`

#### Recommended Profiles

| Use Case | Profile | Reason |
|----------|---------|--------|
| Home directories | `vast_nfs` | Standard performance, shared access |
| Shared applications | `vast_nfs` | Standard performance, read-heavy |
| Datasets (read-only) | `vast_nfs` | Standard performance, read-only |
| Scratch space | `vast_nfs_performance` | High throughput, large I/O |
| Checkpoints | `vast_nfs_performance` | High throughput, write-heavy |

#### Performance Tuning

**Standard Configuration (`vast_nfs`):**
- Default NFS buffer sizes
- Suitable for most workloads
- Lower memory overhead

**High-Performance Configuration (`vast_nfs_performance`):**
- 1MB read/write buffers
- Optimized for large sequential I/O
- Higher memory usage
- Best for scratch, checkpoints, large datasets

---

### PowerVault iSCSI Storage

**Overview:** Dell PowerVault provides block-level iSCSI storage for persistent data and databases.

#### Configuration Format

```yaml
# 1. Configure PowerVault connection
powervault_config:
  ip:
    - 172.1.2.3
    - 172.1.2.4
  port: 3260
  iscsi_initiator: "iqn.2025-01.com.dell:scontrol-node"
  volume_id: "00c0ff4343f1f1f1001c8c4e6901000000"

# 2. Mount PowerVault persistent storage
mounts:
  - name: "powervault_slurm_persist"
    source: "UUID=<uuid-from-blkid>"
    mount_point: "/mnt/slurm-persist"
    mount_default_field: "powervault_iscsi"
    roles: ["slurm_control_node"]

  # 3. Bind mount for MySQL
  - name: "powervault_mysql_bind"
    source: "/mnt/slurm-persist/mysql"
    mount_point: "/var/lib/mysql"
    mount_default_field: "bind_mounts"
    roles: ["slurm_control_node"]

  # 4. Bind mount for Slurm spool
  - name: "powervault_spool_bind"
    source: "/mnt/slurm-persist/spool"
    mount_point: "/var/spool"
    mount_default_field: "bind_mounts"
    roles: ["slurm_control_node"]
```

#### Source Format

- **Pattern:** `UUID=<uuid>` or `/dev/mapper/<multipath_device>`
- **Example:** `UUID=12345678-1234-1234-1234-123456789abc`
- **Note:** UUID is preferred for persistence

#### Setup Script Integration

The `setup_iscsi_storage.sh` script automatically:

1. Discovers iSCSI targets from controller IPs
2. Logs in to all discovered targets
3. Configures multipath for redundancy
4. Selects the correct volume using `volume_id`
5. Creates GPT partition table
6. Formats partition with XFS
7. Mounts to `/mnt/slurm-persist` using UUID
8. Creates subdirectories: `mysql/`, `spool/`
9. Sets up bind mounts in `/etc/fstab`

#### Recommended Workflow

```
PowerVault Setup
     ↓
/mnt/slurm-persist (XFS on /dev/mapper/mpatha1)
     ↓
     ├─ mysql/  → bind mount to /var/lib/mysql
     └─ spool/  → bind mount to /var/spool
```

#### Best Practices

- ✅ Use UUID for source (more reliable than device paths)
- ✅ Use XFS filesystem (default in setup script)
- ✅ Create subdirectories for different services
- ✅ Use bind mounts to map subdirectories to system paths
- ✅ Ensure iSCSI service dependency in mount options

---

## Usage Examples

### Example 1: VAST Home Directories

```yaml
mounts:
  - name: "vast_home"
    source: "192.168.1.100:/home"
    mount_point: "/home"
    mount_default_field: "vast_nfs"
    roles: ["slurm_control_node", "slurm_node", "login_node"]
```

**Result:**
- Filesystem: NFSv4
- Mount options: `defaults,nofail,_netdev,noatime,x-systemd.after=cloud-init-network.service`
- Applied to: All Slurm nodes

---

### Example 2: VAST High-Performance Scratch

```yaml
mounts:
  - name: "vast_scratch"
    source: "192.168.1.100:/scratch"
    mount_point: "/scratch"
    mount_default_field: "vast_nfs_performance"
    roles: ["slurm_node"]
```

**Result:**
- Filesystem: NFSv4
- Mount options: `defaults,nofail,_netdev,noatime,nodiratime,rsize=1048576,wsize=1048576`
- Applied to: Compute nodes only
- Performance: 1MB read/write buffers

---

### Example 3: PowerVault Persistent Storage

```yaml
powervault_config:
  ip:
    - 172.1.2.3
    - 172.1.2.4
  port: 3260
  iscsi_initiator: "iqn.2025-01.com.dell:scontrol-node"
  volume_id: "00c0ff4343f1f1f1001c8c4e6901000000"

mounts:
  - name: "powervault_slurm_persist"
    source: "UUID=<uuid-from-blkid>"
    mount_point: "/mnt/slurm-persist"
    mount_default_field: "powervault_iscsi"
    roles: ["slurm_control_node"]
```

**Result:**
- Filesystem: XFS
- Mount options: `defaults,_netdev,noatime,x-systemd.requires=iscsi.service`
- Applied to: Control node only
- Setup: Automated via `setup_iscsi_storage.sh`

---

### Example 4: PowerVault Bind Mounts

```yaml
mounts:
  # Main persistent storage
  - name: "powervault_slurm_persist"
    source: "UUID=<uuid-from-blkid>"
    mount_point: "/mnt/slurm-persist"
    mount_default_field: "powervault_iscsi"
    roles: ["slurm_control_node"]

  # MySQL data directory
  - name: "powervault_mysql_bind"
    source: "/mnt/slurm-persist/mysql"
    mount_point: "/var/lib/mysql"
    mount_default_field: "bind_mounts"
    roles: ["slurm_control_node"]

  # Slurm spool directory
  - name: "powervault_spool_bind"
    source: "/mnt/slurm-persist/spool"
    mount_point: "/var/spool"
    mount_default_field: "bind_mounts"
    roles: ["slurm_control_node"]
```

**Result:**
- Main mount: `/mnt/slurm-persist` (XFS on iSCSI)
- Bind mount 1: `/var/lib/mysql` → `/mnt/slurm-persist/mysql`
- Bind mount 2: `/var/spool` → `/mnt/slurm-persist/spool`
- All on control node only

---

### Example 5: Explicit Override

```yaml
mounts:
  - name: "vast_apps_custom"
    source: "192.168.1.100:/apps"
    mount_point: "/opt/apps"
    fs_type: "nfs4"                              # ← EXPLICIT
    mnt_opts: "defaults,nofail,_netdev,ro"      # ← EXPLICIT (read-only)
    mount_default_field: "network_storage"
    # Only dump_freq and fsck_pass from profile
    roles: ["slurm_control_node", "slurm_node"]
```

**Result:**
- Filesystem: NFSv4 (explicit, not from profile)
- Mount options: `defaults,nofail,_netdev,ro` (explicit, read-only)
- Dump frequency: `0` (from profile)
- Fsck pass: `0` (from profile)

---

## Priority Resolution

When a mount entry references a profile, field values are resolved using this priority order:

### Priority Order (Highest to Lowest)

```
1. Explicit value in mount entry          ← HIGHEST PRIORITY
2. Value from mount_default_field profile
3. Auto-selected profile based on fs_type
4. Global fallback profile
5. Hardcoded system defaults              ← LOWEST PRIORITY
```

### Resolution Examples

#### Example 1: Full Profile Usage

```yaml
mount_default_fields:
  vast_nfs:
    fs_type: "nfs4"
    mnt_opts: "defaults,nofail,_netdev,noatime"
    dump_freq: "0"
    fsck_pass: "0"

mounts:
  - name: "vast_home"
    source: "192.168.1.100:/home"
    mount_point: "/home"
    mount_default_field: "vast_nfs"
    roles: ["slurm_node"]
```

**Resolution:**
- `fs_type`: `"nfs4"` ← from `vast_nfs` profile
- `mnt_opts`: `"defaults,nofail,_netdev,noatime"` ← from `vast_nfs` profile
- `dump_freq`: `"0"` ← from `vast_nfs` profile
- `fsck_pass`: `"0"` ← from `vast_nfs` profile

---

#### Example 2: Partial Override

```yaml
mount_default_fields:
  vast_nfs:
    fs_type: "nfs4"
    mnt_opts: "defaults,nofail,_netdev,noatime"
    dump_freq: "0"
    fsck_pass: "0"

mounts:
  - name: "vast_apps"
    source: "192.168.1.100:/apps"
    mount_point: "/opt/apps"
    fs_type: "nfs4"                         # ← EXPLICIT
    mnt_opts: "defaults,nofail,_netdev,ro"  # ← EXPLICIT
    mount_default_field: "vast_nfs"
    roles: ["slurm_node"]
```

**Resolution:**
- `fs_type`: `"nfs4"` ← **EXPLICIT (priority 1)** - profile value ignored
- `mnt_opts`: `"defaults,nofail,_netdev,ro"` ← **EXPLICIT (priority 1)** - profile value ignored
- `dump_freq`: `"0"` ← from `vast_nfs` profile (priority 2)
- `fsck_pass`: `"0"` ← from `vast_nfs` profile (priority 2)

---

#### Example 3: No Profile Specified

```yaml
mounts:
  - name: "vast_data"
    source: "192.168.1.100:/data"
    mount_point: "/data"
    fs_type: "nfs4"
    mnt_opts: "defaults,nofail,_netdev"
    dump_freq: "0"
    fsck_pass: "0"
    roles: ["slurm_node"]
```

**Resolution:**
- `fs_type`: `"nfs4"` ← EXPLICIT (priority 1)
- `mnt_opts`: `"defaults,nofail,_netdev"` ← EXPLICIT (priority 1)
- `dump_freq`: `"0"` ← EXPLICIT (priority 1)
- `fsck_pass`: `"0"` ← EXPLICIT (priority 1)
- No profile needed - all fields explicit

---

## Best Practices

### Profile Design

✅ **DO:**
- Create profiles for common storage patterns
- Use descriptive profile names (`vast_nfs`, `powervault_iscsi`)
- Document profile purpose and use cases
- Keep profiles simple and focused

❌ **DON'T:**
- Include roles in profiles (roles belong in mount entries)
- Create too many similar profiles
- Use generic names like `profile1`, `profile2`

---

### Mount Configuration

✅ **DO:**
- Use profiles for standard configurations
- Override specific fields when needed
- Use UUID for PowerVault sources
- Specify roles for each mount
- Use descriptive mount names

❌ **DON'T:**
- Duplicate mount options across entries (use profiles)
- Mix explicit and profile values unnecessarily
- Use device paths for PowerVault (use UUID)
- Forget to specify roles

---

### Storage Selection

| Requirement | Recommended Storage | Profile |
|-------------|---------------------|---------|
| Shared home directories | VAST NFS | `vast_nfs` |
| Shared applications | VAST NFS | `vast_nfs` |
| High-throughput scratch | VAST NFS | `vast_nfs_performance` |
| Large datasets | VAST NFS | `vast_nfs_performance` |
| Persistent databases | PowerVault iSCSI | `powervault_iscsi` |
| Slurm state files | PowerVault iSCSI | `powervault_iscsi` |
| Local scratch | Local disk | `scratch_storage` |

---

### Performance Optimization

#### VAST NFS

**Standard Workloads (`vast_nfs`):**
- Home directories
- Shared applications
- Small file I/O
- Metadata-heavy operations

**High-Performance Workloads (`vast_nfs_performance`):**
- Scratch space
- Checkpointing
- Large sequential I/O
- Streaming data

**Buffer Size Tuning:**
```yaml
# Standard: Default buffers (typically 32KB-128KB)
mnt_opts: "defaults,nofail,_netdev,noatime"

# High-performance: 1MB buffers
mnt_opts: "defaults,nofail,_netdev,noatime,nodiratime,rsize=1048576,wsize=1048576"
```

#### PowerVault iSCSI

**Filesystem Choice:**
- ✅ **XFS** (recommended) - High performance, scalability, large files
- ⚠️ **ext4** - Good compatibility, lower performance at scale

**Mount Options:**
```yaml
# Recommended
mnt_opts: "defaults,_netdev,noatime,x-systemd.requires=iscsi.service"

# Additional options for databases
mnt_opts: "defaults,_netdev,noatime,nobarrier,x-systemd.requires=iscsi.service"
```

---

## Validation Rules

### Required Fields

#### Mount Entry

- ✅ `name` - Unique identifier
- ✅ `source` - Device or network path
- ✅ `mount_point` - Mount point path
- ✅ `roles` - List of target roles
- ✅ **At least one of:**
  - `mount_default_field` (references a profile), OR
  - `mnt_opts` (explicit mount options)

#### Profile

- ✅ `fs_type` - Filesystem type
- ✅ `mnt_opts` - Mount options
- ✅ `dump_freq` - Dump frequency
- ✅ `fsck_pass` - Fsck pass number

---

### Field Validation

#### `name`
- Pattern: `^[a-zA-Z0-9_-]+$`
- Length: 1-64 characters
- Must be unique across all mounts

#### `source`
- Minimum length: 1 character
- Examples:
  - `/dev/sda1`
  - `UUID=12345678-1234-1234-1234-123456789abc`
  - `192.168.1.100:/export/share`

#### `mount_point`
- Pattern: `^/[a-zA-Z0-9/_.-]*$`
- Must start with `/`

#### `fs_type`
- Allowed values: `auto`, `ext2`, `ext3`, `ext4`, `xfs`, `btrfs`, `nfs`, `nfs4`, `cifs`, `tmpfs`, `cephfs`, `vfat`, `ntfs`, `none`

#### `mnt_opts`
- Pattern: `^[a-zA-Z0-9,=._-]+$`
- Examples: `defaults,nofail,_netdev`

#### `dump_freq`
- Pattern: `^[0-2]$`
- Usually `0` (no dump)

#### `fsck_pass`
- Pattern: `^[0-9]$`
- Common values:
  - `0` - No fsck (network filesystems, bind mounts)
  - `1` - Root filesystem
  - `2` - Other local filesystems

#### `roles`
- Array of strings
- Pattern per role: `^[a-zA-Z0-9_-]+$`
- Must be unique within array
- Examples: `slurm_control_node`, `slurm_node`, `login_node`

---

### Profile Validation

#### Profile Name (Key)
- Pattern: `^[a-zA-Z0-9_-]+$`
- Must be unique across all profiles
- Examples: `vast_nfs`, `powervault_iscsi`, `network_storage`

#### Profile Structure
```json
{
  "type": "object",
  "properties": {
    "fs_type": { "type": "string", "enum": [...] },
    "mnt_opts": { "type": "string", "pattern": "^[a-zA-Z0-9,=._-]+$" },
    "dump_freq": { "type": "string", "pattern": "^[0-2]$" },
    "fsck_pass": { "type": "string", "pattern": "^[0-9]$" }
  },
  "required": ["fs_type", "mnt_opts", "dump_freq", "fsck_pass"],
  "additionalProperties": false
}
```

---

### Conditional Validation

#### Mount Entry Must Have Profile OR Explicit Options

```json
{
  "anyOf": [
    { "required": ["mount_default_field"] },
    { "required": ["mnt_opts"] }
  ]
}
```

**Valid:**
```yaml
# Has mount_default_field
- name: "mount1"
  source: "..."
  mount_point: "..."
  mount_default_field: "vast_nfs"
  roles: [...]

# Has mnt_opts
- name: "mount2"
  source: "..."
  mount_point: "..."
  mnt_opts: "defaults,nofail"
  roles: [...]

# Has both (explicit wins)
- name: "mount3"
  source: "..."
  mount_point: "..."
  mount_default_field: "vast_nfs"
  mnt_opts: "defaults,nofail,ro"  # Overrides profile
  roles: [...]
```

**Invalid:**
```yaml
# Missing both mount_default_field and mnt_opts
- name: "mount_invalid"
  source: "..."
  mount_point: "..."
  roles: [...]
```

---

## Quick Reference

### Profile Selection Guide

| Storage Type | Use Case | Profile | Key Features |
|--------------|----------|---------|--------------|
| **VAST** | Home directories | `vast_nfs` | NFSv4, standard perf |
| **VAST** | Shared apps | `vast_nfs` | NFSv4, standard perf |
| **VAST** | Scratch space | `vast_nfs_performance` | NFSv4, 1MB buffers |
| **VAST** | Large datasets | `vast_nfs_performance` | NFSv4, 1MB buffers |
| **PowerVault** | Persistent storage | `powervault_iscsi` | XFS, iSCSI service |
| **PowerVault** | Database bind | `bind_mounts` | Bind from persistent |
| **Generic** | Network FS | `network_storage` | Auto-detect FS |
| **Local** | Local disk | `local_storage` | Auto-detect FS |
| **Local** | Scratch | `scratch_storage` | XFS, optimized |

---

### Common Mount Options

| Option | Description | Use Case |
|--------|-------------|----------|
| `defaults` | Use default options | All mounts |
| `nofail` | Don't fail boot if mount fails | Network mounts |
| `_netdev` | Network device (wait for network) | Network mounts |
| `noatime` | Don't update access time | Performance |
| `nodiratime` | Don't update directory access time | Performance |
| `ro` | Read-only | Shared apps, datasets |
| `rw` | Read-write | Default |
| `bind` | Bind mount | Subdirectory mounts |
| `rsize=1048576` | 1MB read buffer | High-perf NFS |
| `wsize=1048576` | 1MB write buffer | High-perf NFS |
| `x-systemd.requires=iscsi.service` | Require iSCSI service | PowerVault |
| `x-systemd.after=cloud-init-network.service` | Wait for cloud-init network | Network mounts |

---

### Filesystem Types

| Type | Description | Use Case |
|------|-------------|----------|
| `nfs` | NFS version 3 | Legacy NFS |
| `nfs4` | NFS version 4 | Modern NFS (VAST) |
| `xfs` | XFS filesystem | PowerVault, local disks |
| `ext4` | ext4 filesystem | Local disks |
| `cifs` | SMB/CIFS | Windows shares |
| `none` | No filesystem | Bind mounts |
| `auto` | Auto-detect | Generic mounts |

---

## Troubleshooting

### Common Issues

#### Issue: Mount fails with "mount.nfs: Connection timed out"

**Cause:** Network not ready or VAST server unreachable

**Solution:**
- Ensure `_netdev` and `x-systemd.after=cloud-init-network.service` in mount options
- Verify VAST server IP is correct and reachable
- Check firewall rules (NFS ports: 2049, 111)

---

#### Issue: PowerVault mount fails with "No such device"

**Cause:** iSCSI service not running or multipath device not ready

**Solution:**
- Ensure `x-systemd.requires=iscsi.service` in mount options
- Verify `powervault_config` is correctly configured
- Check iSCSI discovery: `iscsiadm -m discovery -t sendtargets -p <IP>`
- Check multipath devices: `multipath -ll`

---

#### Issue: Bind mount fails with "mount point does not exist"

**Cause:** Source directory doesn't exist

**Solution:**
- Ensure parent mount is mounted first
- Create source directory: `mkdir -p /mnt/slurm-persist/mysql`
- Check mount order in configuration

---

#### Issue: Validation error "must have either mount_default_field or mnt_opts"

**Cause:** Mount entry missing both profile reference and explicit mount options

**Solution:**
- Add `mount_default_field: "profile_name"`, OR
- Add `mnt_opts: "mount_options"`

---

## References

### Related Files

- **Configuration:** `input/storage_config.yml`
- **Schema:** `common/library/module_utils/input_validation/schema/storage_config.json`
- **Cloud-Init Template:** `discovery/roles/configure_ochami/templates/cloud_init/ci-group-*.yaml.j2`
- **PowerVault Setup Script:** Embedded in cloud-init template (`setup_iscsi_storage.sh`)

### External Documentation

- [VAST Data Documentation](https://support.vastdata.com/)
- [Dell PowerVault ME5 Series](https://www.dell.com/support/home/en-us/product-support/product/powervault-me5/docs)
- [Linux NFS Client Documentation](https://www.kernel.org/doc/Documentation/filesystems/nfs/nfs-client.txt)
- [Open-iSCSI Documentation](https://github.com/open-iscsi/open-iscsi)
- [XFS Filesystem Documentation](https://www.kernel.org/doc/html/latest/admin-guide/xfs.html)

---

## Changelog

### Version 1.0 (2026-03-20)

- Initial design document
- Added VAST NFS profiles (`vast_nfs`, `vast_nfs_performance`)
- Added PowerVault iSCSI profile (`powervault_iscsi`)
- Removed `roles` field from profiles (roles only in mount entries)
- Changed `mount_default_fields` from array to mapping structure
- Added conditional validation (mount_default_field OR mnt_opts required)
- Updated examples to reflect VAST and PowerVault storage
- Aligned PowerVault examples with `setup_iscsi_storage.sh` implementation

---

## Contact

For questions or issues, please contact the Omnia development team.

---

**End of Document**
