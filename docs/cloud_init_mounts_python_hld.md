# High-Level Design: Cloud-Init Mounts Configuration

## Overview

This document describes the design for a flexible, cloud-init compatible mount and swap configuration system that allows administrators to define storage mounts and swap files with fine-grained control over which nodes receive each configuration.

## Design Goals

1. **Flexibility**: Support multiple mount and swap configurations with different targets
2. **Cloud-Init Compatibility**: Generate configurations compatible with cloud-init's mounts module
3. **Granular Control**: Allow targeting specific nodes by roles, hostnames, or groups
4. **Simplicity**: Provide an intuitive YAML-based configuration interface
5. **Uniqueness**: Ensure each mount/swap configuration is uniquely identifiable

## Architecture

### 1. Configuration Input Structure

The system accepts two main configuration lists in `storage_config.yml`:

#### 1.1 Mounts Configuration

```yaml
mounts:
  - name: "nfs_slurm_home"              # Unique identifier
    fs_spec: "192.168.1.100:/export"    # Device/source
    fs_file: "/home"                    # Mount point
    fs_vfstype: "nfs"                   # Filesystem type
    fs_mntops: "defaults,nofail,_netdev" # Mount options
    fs_freq: "0"                        # Dump frequency
    fs_passno: "0"                      # Fsck pass number
    roles: ["slurm_control_node", "slurm_node"]  # Target roles
    hostnames: ["node01", "node02"]     # Target specific hosts
    groups: ["grp1", "grp2"]            # Target node groups
```

#### 1.2 Swap Configuration

```yaml
swap:
  - name: "compute_swap"                # Unique identifier
    filename: "/swapfile"               # Swap file path
    size: "4G"                          # Swap size
    maxsize: "8G"                       # Maximum size (for auto)
    roles: ["slurm_node"]               # Target roles
    hostnames: []                       # Target specific hosts
    groups: ["grp1"]                    # Target node groups
```

### 2. Target Resolution Process

The system resolves mount/swap targets through a multi-stage process:

```
┌─────────────────────────────────────────────────────────────┐
│  Stage 1: Parse Configuration                               │
│  - Read mounts[] and swap[] from storage_config.yml         │
│  - Read pxe_mapping_file.csv for hostname mappings          │
│  - Validate required fields (name, fs_spec, fs_file, etc.)  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage 2: Resolve Targeting Criteria                        │
│  For each mount/swap entry:                                 │
│    - Extract roles[], hostnames[], groups[]                 │
│    - If all empty → target = ALL nodes from pxe_mapping.csv │
│    - If any specified → resolve to hostname list            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage 3: Convert to Unique Hostname List                   │
│  - roles[] → query pxe_mapping.csv for role-matched hosts   │
│  - hostnames[] → validate against pxe_mapping.csv           │
│  - groups[] → query pxe_mapping.csv for group members       │
│  - Combine all sources into unique hostname set             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage 4: Build Hostname-to-Mounts Mapping                  │
│  For each unique hostname:                                  │
│    hostname_mounts[hostname] = [mount_name1, mount_name2]   │
│    hostname_swaps[hostname] = [swap_name1, swap_name2]      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage 5: Generate Cloud-Init Configuration                 │
│  For each hostname:                                         │
│    - Retrieve mount configurations by mount_name            │
│    - Retrieve swap configurations by swap_name              │
│    - Generate cloud-init YAML for that specific host        │
└─────────────────────────────────────────────────────────────┘
```

### 3. Hostname Resolution Algorithm

#### 3.1 PXE Mapping File Structure

The `pxe_mapping_file.csv` is the source of truth for all hostname mappings. It contains:
- **HOSTNAME**: Unique hostname for each node
- **MAC**: MAC address of the node
- **IP**: IP address of the node
- **SERVICE_TAG**: Service tag of the node
- **ADMIN_MAC**: Admin network MAC address
- **ADMIN_IP**: Admin network IP address
- **BMC_IP**: BMC/iDRAC IP address
- **GROUP_NAME**: Group identifier (e.g., grp0, grp1, grp2)
- **NODE_ROLE**: Role assignment (e.g., slurm_control_node, slurm_node, kube_node)

#### 3.2 Resolution Logic

For each mount/swap configuration entry:

```python
def resolve_hostnames(mount_config, pxe_mapping):
    """
    Resolve roles, hostnames, and groups to a unique list of hostnames.
    All hostname data is sourced from pxe_mapping_file.csv.
    
    Args:
        mount_config: Mount/swap configuration dict
        pxe_mapping: Parsed pxe_mapping_file.csv data (DataFrame)
    
    Returns:
        Set of unique hostnames
    """
    target_hostnames = set()
    
    # If all targeting fields are empty, return ALL nodes from pxe_mapping
    if not (mount_config.get('roles') or 
            mount_config.get('hostnames') or 
            mount_config.get('groups')):
        return set(pxe_mapping['HOSTNAME'].tolist())
    
    # Resolve roles to hostnames from pxe_mapping
    for role in mount_config.get('roles', []):
        matching_hosts = pxe_mapping[
            pxe_mapping['NODE_ROLE'] == role
        ]['HOSTNAME'].tolist()
        target_hostnames.update(matching_hosts)
    
    # Validate and add explicit hostnames from pxe_mapping
    for hostname in mount_config.get('hostnames', []):
        if hostname in pxe_mapping['HOSTNAME'].values:
            target_hostnames.add(hostname)
        else:
            log_warning(f"Hostname '{hostname}' not found in pxe_mapping.csv")
    
    # Resolve groups to hostnames from pxe_mapping
    for group in mount_config.get('groups', []):
        matching_hosts = pxe_mapping[
            pxe_mapping['GROUP_NAME'] == group
        ]['HOSTNAME'].tolist()
        target_hostnames.update(matching_hosts)
    
    return target_hostnames
```

#### 3.3 Example Resolution

**PXE Mapping File (pxe_mapping_file.csv):**
```csv
HOSTNAME,MAC,IP,SERVICE_TAG,GROUP_NAME,NODE_ROLE
manager01,aa:bb:cc:dd:ee:01,192.168.1.10,SVC001,grp0,slurm_control_node
compute01,aa:bb:cc:dd:ee:02,192.168.1.11,SVC002,grp1,slurm_node
compute02,aa:bb:cc:dd:ee:03,192.168.1.12,SVC003,grp1,slurm_node
compute03,aa:bb:cc:dd:ee:04,192.168.1.13,SVC004,grp2,slurm_node
node01,aa:bb:cc:dd:ee:05,192.168.1.14,SVC005,grp1,kube_node
node02,aa:bb:cc:dd:ee:06,192.168.1.15,SVC006,grp1,kube_node
```

**Configuration:**
```yaml
mounts:
  - name: "nfs_home"
    fs_spec: "192.168.1.100:/home"
    fs_file: "/home"
    roles: ["slurm_node"]
    hostnames: ["manager01"]
    groups: ["grp1"]
```

**Resolution Steps:**

1. **Roles Resolution**: `["slurm_node"]` → Query pxe_mapping.csv where NODE_ROLE='slurm_node' → `["compute01", "compute02", "compute03"]`
2. **Hostnames**: `["manager01"]` → Validate in pxe_mapping.csv → `["manager01"]`
3. **Groups Resolution**: `["grp1"]` → Query pxe_mapping.csv where GROUP_NAME='grp1' → `["compute01", "compute02", "node01", "node02"]`
4. **Unique Set**: `{"compute01", "compute02", "compute03", "manager01", "node01", "node02"}`

### 4. Hostname-to-Mounts Mapping

After resolving all mount and swap configurations, the system builds a reverse mapping:

```python
hostname_to_mounts = {
    "compute01": ["nfs_home", "data_mount", "compute_swap"],
    "compute02": ["nfs_home", "data_mount", "compute_swap"],
    "manager01": ["nfs_home", "nfs_slurm"],
    "node01": ["nfs_home", "ephemeral_mount"],
    # ... etc
}
```

**Data Structure:**
```python
{
    "hostname": {
        "mounts": [
            {
                "name": "mount_name",
                "fs_spec": "...",
                "fs_file": "...",
                "fs_vfstype": "...",
                "fs_mntops": "...",
                "fs_freq": "...",
                "fs_passno": "..."
            }
        ],
        "swap": [
            {
                "name": "swap_name",
                "filename": "...",
                "size": "...",
                "maxsize": "..."
            }
        ]
    }
}
```

### 5. Cloud-Init Configuration Generation

For each hostname, generate a cloud-init compatible configuration:

#### 5.1 Cloud-Init Format

```yaml
#cloud-config
mounts:
  - ["192.168.1.100:/home", "/home", "nfs", "defaults,nofail,_netdev", "0", "0"]
  - ["/dev/sdc", "/opt/data", "ext4", "defaults,nofail", "0", "2"]

mount_default_fields: ["auto", "defaults,nofail,x-systemd.after=cloud-init-network.service", "0", "2"]

swap:
  filename: /swapfile
  size: 4G
  maxsize: 8G
```

#### 5.2 Generation Process

```python
def generate_cloud_init_for_host(hostname, hostname_config):
    """
    Generate cloud-init configuration for a specific host.
    
    Args:
        hostname: Target hostname
        hostname_config: Dict containing mounts and swap configs
    
    Returns:
        Cloud-init YAML string
    """
    cloud_init = {
        'mounts': [],
        'mount_default_fields': mount_default_fields,
        'swap': {}
    }
    
    # Convert mounts to cloud-init format
    for mount in hostname_config['mounts']:
        cloud_init['mounts'].append([
            mount['fs_spec'],
            mount['fs_file'],
            mount.get('fs_vfstype', 'auto'),
            mount.get('fs_mntops', 'defaults,nofail'),
            mount.get('fs_freq', '0'),
            mount.get('fs_passno', '2')
        ])
    
    # Add swap configuration (use first swap if multiple)
    if hostname_config['swap']:
        swap = hostname_config['swap'][0]
        cloud_init['swap'] = {
            'filename': swap['filename'],
            'size': swap['size'],
            'maxsize': swap.get('maxsize', '')
        }
    
    return yaml.dump(cloud_init)
```

### 6. Deployment Flow

```
┌──────────────────┐
│ Administrator    │
│ edits            │
│ storage_config   │
└────────┬─────────┘
         │
         ↓
┌──────────────────────────────────────────┐
│ Ansible Playbook Execution               │
│ 1. Read storage_config.yml               │
│ 2. Read inventory (roles)                │
│ 3. Read pxe_mapping_file.csv (groups)    │
└────────┬─────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────┐
│ Resolution Engine                        │
│ - Resolve all mounts/swaps to hostnames  │
│ - Build hostname_to_mounts mapping       │
└────────┬─────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────┐
│ Cloud-Init Generator                     │
│ For each hostname:                       │
│   - Generate cloud-init YAML             │
│   - Write to /var/lib/cloud-init/...     │
└────────┬─────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────┐
│ Node Provisioning                        │
│ - Cloud-init reads configuration         │
│ - Mounts filesystems                     │
│ - Creates swap files                     │
└──────────────────────────────────────────┘
```

## Data Flow Example

### Input Configuration

```yaml
mounts:
  - name: "nfs_slurm_home"
    fs_spec: "172.16.107.168:/mnt/share/omnia"
    fs_file: "/home"
    fs_vfstype: "nfs"
    fs_mntops: "defaults,nofail,_netdev"
    fs_freq: "0"
    fs_passno: "0"
    roles: ["slurm_control_node", "slurm_node"]
    hostnames: []
    groups: []

  - name: "local_data"
    fs_spec: "/dev/sdc"
    fs_file: "/opt/data"
    fs_vfstype: "ext4"
    fs_mntops: "defaults,nofail"
    fs_freq: "0"
    fs_passno: "2"
    roles: []
    hostnames: []
    groups: ["grp1"]

swap:
  - name: "compute_swap"
    filename: "/swapfile"
    size: "4G"
    maxsize: "8G"
    roles: ["slurm_node"]
    hostnames: []
    groups: []
```

### Resolution Results

**PXE Mapping Data (pxe_mapping_file.csv):**

| HOSTNAME | NODE_ROLE | GROUP_NAME |
|----------|-----------|------------|
| manager01 | slurm_control_node | grp0 |
| compute01 | slurm_node | grp1 |
| compute02 | slurm_node | grp1 |
| compute03 | slurm_node | grp2 |

**Resolution from pxe_mapping.csv:**
- Role `slurm_control_node`: `["manager01"]`
- Role `slurm_node`: `["compute01", "compute02", "compute03"]`
- Group `grp1`: `["compute01", "compute02"]`

**Resolved Hostnames per Mount:**

| Mount Name | Resolved Hostnames |
|------------|-------------------|
| nfs_slurm_home | manager01, compute01, compute02, compute03 |
| local_data | compute01, compute02 |

**Resolved Hostnames per Swap:**

| Swap Name | Resolved Hostnames |
|-----------|-------------------|
| compute_swap | compute01, compute02, compute03 |

### Hostname-to-Mounts Mapping

```python
{
    "manager01": {
        "mounts": ["nfs_slurm_home"],
        "swap": []
    },
    "compute01": {
        "mounts": ["nfs_slurm_home", "local_data"],
        "swap": ["compute_swap"]
    },
    "compute02": {
        "mounts": ["nfs_slurm_home", "local_data"],
        "swap": ["compute_swap"]
    },
    "compute03": {
        "mounts": ["nfs_slurm_home"],
        "swap": ["compute_swap"]
    }
}
```

### Generated Cloud-Init for compute01

```yaml
#cloud-config
mounts:
  - ["172.16.107.168:/mnt/share/omnia", "/home", "nfs", "defaults,nofail,_netdev", "0", "0"]
  - ["/dev/sdc", "/opt/data", "ext4", "defaults,nofail", "0", "2"]

mount_default_fields: ["auto", "defaults,nofail,x-systemd.after=cloud-init-network.service", "0", "2"]

swap:
  filename: /swapfile
  size: 4G
  maxsize: 8G
```

## Key Design Decisions

### 1. Unique Mount Names
- Each mount/swap must have a unique `name` field
- Enables tracking, debugging, and idempotent operations
- Allows referencing specific configurations in logs and errors

### 2. List-Based Targeting
- Support multiple targeting methods: roles, hostnames, groups
- Union of all targeting criteria (OR logic)
- Empty targeting = apply to ALL nodes

### 3. Hostname-Centric Processing
- Convert all targeting to unique hostname lists early
- Build hostname-to-mounts mapping for efficient lookup
- Generate per-host cloud-init configurations

### 4. Cloud-Init Compatibility
- Follow cloud-init mounts module specification exactly
- Support all /etc/fstab fields
- Provide sensible defaults via `mount_default_fields`

### 5. Separation of Concerns
- Configuration input (YAML)
- Resolution logic (roles/groups → hostnames)
- Cloud-init generation (per-host YAML)
- Deployment (Ansible/cloud-init)

## Implementation Considerations

### 1. Validation
- Validate unique mount/swap names
- Validate required fields (name, fs_spec, fs_file)
- Validate targeting criteria reference valid roles/groups
- Validate filesystem types are supported

### 2. Error Handling
- Invalid role names → warning and skip
- Invalid group names → warning and skip
- Invalid hostnames → warning and skip
- No resolved hostnames → error

### 3. Idempotency
- Use mount names for tracking applied configurations
- Support updates to existing mounts
- Support removal of mounts (empty fs_file)

### 4. Performance
- Cache hostname resolution results
- Batch cloud-init generation
- Parallel deployment where possible

## Security Considerations

1. **Credential Management**: For CIFS/SMB mounts, credentials should be stored securely (e.g., `/root/.smbcreds` with 0600 permissions)
2. **Mount Options**: Use `nofail` to prevent boot failures
3. **Network Mounts**: Use `_netdev` to ensure network is available before mounting
4. **Validation**: Validate all user inputs to prevent injection attacks

## Future Enhancements

1. **Conditional Mounting**: Support conditional mounts based on hardware detection
2. **Mount Dependencies**: Support mount ordering/dependencies
3. **Dynamic Updates**: Support runtime mount updates without reboot
4. **Monitoring Integration**: Integration with monitoring systems for mount health
5. **Backup/Restore**: Configuration backup and restore capabilities

## Conclusion

This design provides a flexible, scalable approach to managing storage mounts and swap configurations across heterogeneous clusters. By converting roles, hostnames, and groups to unique hostname lists and building hostname-to-mounts mappings, the system can efficiently generate cloud-init configurations tailored to each node's requirements.
