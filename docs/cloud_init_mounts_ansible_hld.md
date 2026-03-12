# High-Level Design: Cloud-Init Mounts Configuration (Ansible Implementation)

## Overview

This document describes an Ansible-based design for a flexible, cloud-init compatible mount and swap configuration system. The implementation uses Ansible roles and Jinja2 templates to manage storage mounts and swap files with fine-grained control over which nodes receive each configuration.

**Key Constraint**: The Ansible controller does not have direct access to the NFS server or storage devices. All operations are executed on target nodes.

## Design Goals

1. **Ansible-Native**: Use Ansible roles, tasks, and Jinja2 templates (no Python modules)
2. **Cloud-Init Compatibility**: Generate configurations compatible with cloud-init's mounts module
3. **Granular Control**: Target specific nodes by roles, hostnames, or groups from pxe_mapping.csv
4. **Idempotency**: Support repeated executions without side effects
5. **No Controller Dependencies**: All storage operations execute on target nodes

## Architecture

### 1. Configuration Input Structure

The system accepts configuration from `storage_config.yml`:

#### 1.1 Mounts Configuration

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

### 2. Simplified Implementation Approach

**New Ansible Module**: `cloud_init_mounts_config`

This module handles all resolution logic and cloud-init configuration generation:

```
storage_generic/
├── library/
│   └── cloud_init_mounts_config.py    # New module
├── roles/
│   └── configure_ochani/              # Existing role - modified
│       ├── tasks/
│       │   ├── main.yml
│       │   └── configure_mounts.yml   # New task file
│       └── templates/
│           └── cloud_init_mounts.yml.j2
└── input/
    └── storage_config.yml
```

### 3. Target Resolution Process (Ansible Implementation)

```
┌─────────────────────────────────────────────────────────────┐
│  Stage 1: Load Configuration (Ansible Controller)           │
│  - include_vars: storage_config.yml                         │
│  - Read pxe_mapping_file.csv using lookup('file')           │
│  - Parse CSV using community.general.read_csv               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage 2: Build PXE Mapping Dictionary (set_fact)           │
│  - Create hostname → attributes mapping                     │
│  - Create role → hostnames mapping                          │
│  - Create group → hostnames mapping                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage 3: Resolve Targets for Each Mount/Swap (Jinja2)      │
│  - For each mount in mounts[]                               │
│  - For each swap in swap[]                                  │
│  - Apply role/hostname/group filters                        │
│  - Build unique hostname list per mount/swap                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage 4: Build Hostname-to-Mounts Mapping (set_fact)       │
│  - Invert mount→hosts to host→mounts mapping                │
│  - Each hostname gets list of applicable mount names        │
│  - Each hostname gets list of applicable swap names         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage 5: Generate Cloud-Init Config (delegate_to)          │
│  - For each target host (delegate_to: {{ item }})           │
│  - Use Jinja2 template to generate cloud-init YAML          │
│  - Write to /etc/cloud/cloud.cfg.d/99-mounts.cfg            │
│  - OR update /etc/fstab directly                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Stage 6: Apply Configuration (on target nodes)             │
│  - Run cloud-init modules apply mounts                      │
│  - OR use ansible.posix.mount module directly               │
│  - Create swap files using command/shell module             │
└─────────────────────────────────────────────────────────────┘
```

### 4. Hostname Resolution Algorithm (Ansible/Jinja2)

#### 4.1 PXE Mapping File Structure

The `pxe_mapping_file.csv` is the source of truth:

```csv
HOSTNAME,MAC,IP,SERVICE_TAG,GROUP_NAME,NODE_ROLE
manager01,aa:bb:cc:dd:ee:01,192.168.1.10,SVC001,grp0,slurm_control_node
compute01,aa:bb:cc:dd:ee:02,192.168.1.11,SVC002,grp1,slurm_node
compute02,aa:bb:cc:dd:ee:03,192.168.1.12,SVC003,grp1,slurm_node
compute03,aa:bb:cc:dd:ee:04,192.168.1.13,SVC004,grp2,slurm_node
```

#### 4.2 Parse PXE Mapping (Ansible Task)

```yaml
# tasks/parse_pxe_mapping.yml
---
- name: Read PXE mapping file
  set_fact:
    pxe_mapping_raw: "{{ lookup('file', pxe_mapping_file_path) }}"

- name: Parse CSV to list of dictionaries
  set_fact:
    pxe_mapping_list: "{{ pxe_mapping_raw | community.general.read_csv }}"

- name: Build hostname to attributes mapping
  set_fact:
    pxe_hostname_map: >-
      {{
        pxe_hostname_map | default({}) | combine({
          item.HOSTNAME: {
            'ip': item.IP,
            'mac': item.MAC,
            'role': item.NODE_ROLE,
            'group': item.GROUP_NAME,
            'service_tag': item.SERVICE_TAG
          }
        })
      }}
  loop: "{{ pxe_mapping_list }}"
  loop_control:
    label: "{{ item.HOSTNAME }}"

- name: Build role to hostnames mapping
  set_fact:
    pxe_role_map: >-
      {{
        pxe_role_map | default({}) | combine({
          item.NODE_ROLE: (pxe_role_map[item.NODE_ROLE] | default([])) + [item.HOSTNAME]
        })
      }}
  loop: "{{ pxe_mapping_list }}"
  loop_control:
    label: "{{ item.HOSTNAME }}"

- name: Build group to hostnames mapping
  set_fact:
    pxe_group_map: >-
      {{
        pxe_group_map | default({}) | combine({
          item.GROUP_NAME: (pxe_group_map[item.GROUP_NAME] | default([])) + [item.HOSTNAME]
        })
      }}
  loop: "{{ pxe_mapping_list }}"
  loop_control:
    label: "{{ item.HOSTNAME }}"

- name: Get all hostnames
  set_fact:
    all_hostnames: "{{ pxe_mapping_list | map(attribute='HOSTNAME') | list }}"
```

#### 4.3 Resolve Targets for Each Mount (Ansible Task)

```yaml
# tasks/resolve_targets.yml
---
- name: Resolve target hostnames for each mount
  set_fact:
    mount_targets: >-
      {{
        mount_targets | default({}) | combine({
          item.name: resolve_mount_targets(item, pxe_role_map, pxe_group_map, all_hostnames)
        })
      }}
  loop: "{{ mounts }}"
  loop_control:
    label: "{{ item.name }}"
  vars:
    resolve_mount_targets: |
      {% set targets = [] %}
      {% set mount = item %}
      
      {# If all targeting fields are empty, use all hostnames #}
      {% if not mount.roles and not mount.hostnames and not mount.groups %}
        {% set targets = all_hostnames %}
      {% else %}
        {# Resolve roles to hostnames #}
        {% for role in mount.roles | default([]) %}
          {% if role in pxe_role_map %}
            {% set targets = targets + pxe_role_map[role] %}
          {% endif %}
        {% endfor %}
        
        {# Add explicit hostnames #}
        {% set targets = targets + (mount.hostnames | default([])) %}
        
        {# Resolve groups to hostnames #}
        {% for group in mount.groups | default([]) %}
          {% if group in pxe_group_map %}
            {% set targets = targets + pxe_group_map[group] %}
          {% endif %}
        {% endfor %}
      {% endif %}
      
      {# Return unique list #}
      {{ targets | unique | list }}

- name: Resolve target hostnames for each swap
  set_fact:
    swap_targets: >-
      {{
        swap_targets | default({}) | combine({
          item.name: resolve_swap_targets(item, pxe_role_map, pxe_group_map, all_hostnames)
        })
      }}
  loop: "{{ swap }}"
  loop_control:
    label: "{{ item.name }}"
  vars:
    resolve_swap_targets: |
      {# Same logic as mount resolution #}
      {% set targets = [] %}
      {% set swap_item = item %}
      
      {% if not swap_item.roles and not swap_item.hostnames and not swap_item.groups %}
        {% set targets = all_hostnames %}
      {% else %}
        {% for role in swap_item.roles | default([]) %}
          {% if role in pxe_role_map %}
            {% set targets = targets + pxe_role_map[role] %}
          {% endif %}
        {% endfor %}
        {% set targets = targets + (swap_item.hostnames | default([])) %}
        {% for group in swap_item.groups | default([]) %}
          {% if group in pxe_group_map %}
            {% set targets = targets + pxe_group_map[group] %}
          {% endif %}
        {% endfor %}
      {% endif %}
      
      {{ targets | unique | list }}
```

#### 4.4 Build Hostname-to-Mounts Mapping (Ansible Task)

```yaml
# tasks/resolve_targets.yml (continued)
---
- name: Build hostname to mounts mapping
  set_fact:
    hostname_mounts: >-
      {{
        hostname_mounts | default({}) | combine({
          hostname: {
            'mounts': get_mounts_for_host(hostname, mount_targets, mounts),
            'swap': get_swap_for_host(hostname, swap_targets, swap)
          }
        })
      }}
  loop: "{{ all_hostnames }}"
  loop_control:
    loop_var: hostname
  vars:
    get_mounts_for_host: |
      {% set host_mounts = [] %}
      {% for mount_name, target_hosts in mount_targets.items() %}
        {% if hostname in target_hosts %}
          {% set mount_config = mounts | selectattr('name', 'equalto', mount_name) | first %}
          {% set host_mounts = host_mounts + [mount_config] %}
        {% endif %}
      {% endfor %}
      {{ host_mounts }}
    
    get_swap_for_host: |
      {% set host_swaps = [] %}
      {% for swap_name, target_hosts in swap_targets.items() %}
        {% if hostname in target_hosts %}
          {% set swap_config = swap | selectattr('name', 'equalto', swap_name) | first %}
          {% set host_swaps = host_swaps + [swap_config] %}
        {% endif %}
      {% endfor %}
      {{ host_swaps }}
```

### 5. Cloud-Init Configuration Generation

#### 5.1 Jinja2 Template for Cloud-Init

```jinja2
{# templates/cloud_init_mounts.yml.j2 #}
#cloud-config
# Generated by Omnia storage_mounts role
# Hostname: {{ inventory_hostname }}
# Generated at: {{ ansible_date_time.iso8601 }}

{% if hostname_mounts[inventory_hostname].mounts | length > 0 %}
mounts:
{% for mount in hostname_mounts[inventory_hostname].mounts %}
  - ["{{ mount.fs_spec }}", "{{ mount.fs_file }}", "{{ mount.fs_vfstype | default('auto') }}", "{{ mount.fs_mntops | default('defaults,nofail') }}", "{{ mount.fs_freq | default('0') }}", "{{ mount.fs_passno | default('2') }}"]
{% endfor %}

mount_default_fields: {{ mount_default_fields | to_json }}
{% endif %}

{% if hostname_mounts[inventory_hostname].swap | length > 0 %}
{% set swap_config = hostname_mounts[inventory_hostname].swap[0] %}
swap:
  filename: {{ swap_config.filename }}
  size: {{ swap_config.size }}
{% if swap_config.maxsize %}
  maxsize: {{ swap_config.maxsize }}
{% endif %}
{% endif %}
```

#### 5.2 Generate and Apply Cloud-Init Configuration

```yaml
# tasks/generate_cloud_init.yml
---
- name: Create cloud-init configuration directory
  file:
    path: /etc/cloud/cloud.cfg.d
    state: directory
    mode: '0755'
  delegate_to: "{{ item }}"
  loop: "{{ all_hostnames }}"
  when: hostname_mounts[item].mounts | length > 0 or hostname_mounts[item].swap | length > 0

- name: Generate cloud-init mounts configuration
  template:
    src: cloud_init_mounts.yml.j2
    dest: /etc/cloud/cloud.cfg.d/99-mounts.cfg
    mode: '0644'
  delegate_to: "{{ item }}"
  loop: "{{ all_hostnames }}"
  when: hostname_mounts[item].mounts | length > 0 or hostname_mounts[item].swap | length > 0
  notify: Apply cloud-init mounts

- name: Apply cloud-init mounts module
  command: cloud-init single --name mounts
  delegate_to: "{{ item }}"
  loop: "{{ all_hostnames }}"
  when: 
    - hostname_mounts[item].mounts | length > 0 or hostname_mounts[item].swap | length > 0
    - apply_cloud_init | default(true)
```

### 6. Alternative: Direct Mount Management (Without Cloud-Init)

For environments where cloud-init is not available or preferred:

```yaml
# tasks/apply_mounts.yml
---
- name: Mount filesystems directly using ansible.posix.mount
  ansible.posix.mount:
    path: "{{ mount_item.fs_file }}"
    src: "{{ mount_item.fs_spec }}"
    fstype: "{{ mount_item.fs_vfstype | default('auto') }}"
    opts: "{{ mount_item.fs_mntops | default('defaults,nofail') }}"
    dump: "{{ mount_item.fs_freq | default('0') }}"
    passno: "{{ mount_item.fs_passno | default('2') }}"
    state: mounted
  delegate_to: "{{ hostname }}"
  loop: "{{ hostname_mounts[hostname].mounts }}"
  loop_control:
    loop_var: mount_item
    label: "{{ mount_item.name }}"
  when: hostname_mounts[hostname].mounts | length > 0
  with_items: "{{ all_hostnames }}"
  loop_control:
    loop_var: hostname

- name: Create swap file
  command: |
    dd if=/dev/zero of={{ swap_item.filename }} bs=1M count={{ swap_item.size | regex_replace('[^0-9]', '') }}
  args:
    creates: "{{ swap_item.filename }}"
  delegate_to: "{{ hostname }}"
  loop: "{{ hostname_mounts[hostname].swap }}"
  loop_control:
    loop_var: swap_item
    label: "{{ swap_item.name }}"
  when: hostname_mounts[hostname].swap | length > 0
  with_items: "{{ all_hostnames }}"
  loop_control:
    loop_var: hostname

- name: Set swap file permissions
  file:
    path: "{{ swap_item.filename }}"
    mode: '0600'
  delegate_to: "{{ hostname }}"
  loop: "{{ hostname_mounts[hostname].swap }}"
  loop_control:
    loop_var: swap_item
    label: "{{ swap_item.name }}"
  when: hostname_mounts[hostname].swap | length > 0
  with_items: "{{ all_hostnames }}"
  loop_control:
    loop_var: hostname

- name: Format swap file
  command: mkswap {{ swap_item.filename }}
  delegate_to: "{{ hostname }}"
  loop: "{{ hostname_mounts[hostname].swap }}"
  loop_control:
    loop_var: swap_item
    label: "{{ swap_item.name }}"
  when: hostname_mounts[hostname].swap | length > 0
  with_items: "{{ all_hostnames }}"
  loop_control:
    loop_var: hostname

- name: Enable swap
  command: swapon {{ swap_item.filename }}
  delegate_to: "{{ hostname }}"
  loop: "{{ hostname_mounts[hostname].swap }}"
  loop_control:
    loop_var: swap_item
    label: "{{ swap_item.name }}"
  when: hostname_mounts[hostname].swap | length > 0
  with_items: "{{ all_hostnames }}"
  loop_control:
    loop_var: hostname

- name: Add swap to /etc/fstab
  lineinfile:
    path: /etc/fstab
    line: "{{ swap_item.filename }} none swap sw 0 0"
    state: present
  delegate_to: "{{ hostname }}"
  loop: "{{ hostname_mounts[hostname].swap }}"
  loop_control:
    loop_var: swap_item
    label: "{{ swap_item.name }}"
  when: hostname_mounts[hostname].swap | length > 0
  with_items: "{{ all_hostnames }}"
  loop_control:
    loop_var: hostname
```

### 7. Main Playbook

```yaml
# playbooks/configure_storage_mounts.yml
---
- name: Configure Storage Mounts and Swap
  hosts: localhost
  gather_facts: false
  vars_files:
    - ../input/storage_config.yml
  vars:
    pxe_mapping_file_path: "/path/to/pxe_mapping_file.csv"
    apply_cloud_init: true  # Set to false to use direct mount management
  
  tasks:
    - name: Parse PXE mapping file
      include_tasks: ../roles/storage_mounts/tasks/parse_pxe_mapping.yml
    
    - name: Resolve mount and swap targets
      include_tasks: ../roles/storage_mounts/tasks/resolve_targets.yml
    
    - name: Display hostname to mounts mapping
      debug:
        var: hostname_mounts
        verbosity: 1
    
    - name: Generate and apply cloud-init configuration
      include_tasks: ../roles/storage_mounts/tasks/generate_cloud_init.yml
      when: apply_cloud_init | default(true)
    
    - name: Apply mounts directly (without cloud-init)
      include_tasks: ../roles/storage_mounts/tasks/apply_mounts.yml
      when: not (apply_cloud_init | default(true))
```

### 8. Data Flow Example

#### Input Configuration

```yaml
# storage_config.yml
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

mount_default_fields: ["auto", "defaults,nofail,x-systemd.after=cloud-init-network.service", "0", "2"]
```

#### PXE Mapping Data

```csv
HOSTNAME,MAC,IP,SERVICE_TAG,GROUP_NAME,NODE_ROLE
manager01,aa:bb:cc:dd:ee:01,192.168.1.10,SVC001,grp0,slurm_control_node
compute01,aa:bb:cc:dd:ee:02,192.168.1.11,SVC002,grp1,slurm_node
compute02,aa:bb:cc:dd:ee:03,192.168.1.12,SVC003,grp1,slurm_node
compute03,aa:bb:cc:dd:ee:04,192.168.1.13,SVC004,grp2,slurm_node
```

#### Ansible Facts Generated

```yaml
# pxe_role_map
pxe_role_map:
  slurm_control_node: ["manager01"]
  slurm_node: ["compute01", "compute02", "compute03"]

# pxe_group_map
pxe_group_map:
  grp0: ["manager01"]
  grp1: ["compute01", "compute02"]
  grp2: ["compute03"]

# mount_targets
mount_targets:
  nfs_slurm_home: ["manager01", "compute01", "compute02", "compute03"]
  local_data: ["compute01", "compute02"]

# swap_targets
swap_targets:
  compute_swap: ["compute01", "compute02", "compute03"]

# hostname_mounts
hostname_mounts:
  manager01:
    mounts:
      - name: "nfs_slurm_home"
        fs_spec: "172.16.107.168:/mnt/share/omnia"
        fs_file: "/home"
        fs_vfstype: "nfs"
        fs_mntops: "defaults,nofail,_netdev"
        fs_freq: "0"
        fs_passno: "0"
    swap: []
  
  compute01:
    mounts:
      - name: "nfs_slurm_home"
        fs_spec: "172.16.107.168:/mnt/share/omnia"
        fs_file: "/home"
        fs_vfstype: "nfs"
        fs_mntops: "defaults,nofail,_netdev"
        fs_freq: "0"
        fs_passno: "0"
      - name: "local_data"
        fs_spec: "/dev/sdc"
        fs_file: "/opt/data"
        fs_vfstype: "ext4"
        fs_mntops: "defaults,nofail"
        fs_freq: "0"
        fs_passno: "2"
    swap:
      - name: "compute_swap"
        filename: "/swapfile"
        size: "4G"
        maxsize: "8G"
  
  compute02:
    mounts:
      - name: "nfs_slurm_home"
        fs_spec: "172.16.107.168:/mnt/share/omnia"
        fs_file: "/home"
        fs_vfstype: "nfs"
        fs_mntops: "defaults,nofail,_netdev"
        fs_freq: "0"
        fs_passno: "0"
      - name: "local_data"
        fs_spec: "/dev/sdc"
        fs_file: "/opt/data"
        fs_vfstype: "ext4"
        fs_mntops: "defaults,nofail"
        fs_freq: "0"
        fs_passno: "2"
    swap:
      - name: "compute_swap"
        filename: "/swapfile"
        size: "4G"
        maxsize: "8G"
  
  compute03:
    mounts:
      - name: "nfs_slurm_home"
        fs_spec: "172.16.107.168:/mnt/share/omnia"
        fs_file: "/home"
        fs_vfstype: "nfs"
        fs_mntops: "defaults,nofail,_netdev"
        fs_freq: "0"
        fs_passno: "0"
    swap:
      - name: "compute_swap"
        filename: "/swapfile"
        size: "4G"
        maxsize: "8G"
```

#### Generated Cloud-Init for compute01

```yaml
#cloud-config
# Generated by Omnia storage_mounts role
# Hostname: compute01
# Generated at: 2026-03-12T13:28:00Z

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

### 1. Ansible-Native Implementation
- **No Python modules**: All logic implemented using Ansible tasks, Jinja2 templates, and filters
- **Controller independence**: No direct access to NFS/storage required from controller
- **delegate_to**: All storage operations execute on target nodes

### 2. PXE Mapping as Source of Truth
- All hostname, role, and group data sourced from `pxe_mapping_file.csv`
- Parsed once at playbook start using `community.general.read_csv`
- Built into efficient lookup dictionaries using `set_fact`

### 3. Two Deployment Modes
- **Cloud-Init Mode**: Generate cloud-init configuration files
- **Direct Mode**: Use `ansible.posix.mount` module directly
- Configurable via `apply_cloud_init` variable

### 4. Idempotency
- Cloud-init configurations are idempotent by design
- `ansible.posix.mount` module ensures idempotent mount operations
- Swap file creation uses `creates` parameter to avoid recreation

### 5. Flexibility
- Support for multiple mounts per host
- Support for multiple swap files per host
- Union logic for roles, hostnames, and groups

## Implementation Considerations

### 1. Performance Optimization

```yaml
# Use async for parallel execution on multiple hosts
- name: Apply mounts on all hosts in parallel
  ansible.posix.mount:
    path: "{{ mount_item.fs_file }}"
    src: "{{ mount_item.fs_spec }}"
    fstype: "{{ mount_item.fs_vfstype }}"
    state: mounted
  delegate_to: "{{ hostname }}"
  async: 300
  poll: 0
  register: mount_async
  loop: "{{ all_hostnames }}"
  loop_control:
    loop_var: hostname

- name: Wait for mount operations to complete
  async_status:
    jid: "{{ item.ansible_job_id }}"
  register: mount_result
  until: mount_result.finished
  retries: 30
  delay: 10
  loop: "{{ mount_async.results }}"
```

### 2. Error Handling

```yaml
- name: Validate mount configuration
  assert:
    that:
      - item.name is defined
      - item.fs_spec is defined
      - item.fs_file is defined
    fail_msg: "Mount configuration missing required fields"
  loop: "{{ mounts }}"
  loop_control:
    label: "{{ item.name | default('unnamed') }}"

- name: Check if NFS server is reachable (from target nodes)
  wait_for:
    host: "{{ item.fs_spec.split(':')[0] }}"
    port: 2049
    timeout: 10
  delegate_to: "{{ hostname }}"
  when: item.fs_vfstype == 'nfs'
  ignore_errors: true
  register: nfs_check
```

### 3. Validation

```yaml
- name: Validate unique mount names
  assert:
    that:
      - mounts | map(attribute='name') | list | length == mounts | map(attribute='name') | unique | list | length
    fail_msg: "Duplicate mount names found"

- name: Validate hostnames exist in PXE mapping
  assert:
    that:
      - item in all_hostnames
    fail_msg: "Hostname {{ item }} not found in pxe_mapping.csv"
  loop: "{{ mounts | map(attribute='hostnames') | flatten | unique }}"
  when: item | length > 0
```

### 4. Logging and Debugging

```yaml
- name: Log mount resolution
  debug:
    msg: |
      Mount: {{ item.key }}
      Targets: {{ item.value | join(', ') }}
  loop: "{{ mount_targets | dict2items }}"
  loop_control:
    label: "{{ item.key }}"

- name: Create mount application log
  copy:
    content: |
      Hostname: {{ inventory_hostname }}
      Mounts Applied: {{ hostname_mounts[inventory_hostname].mounts | map(attribute='name') | join(', ') }}
      Swap Applied: {{ hostname_mounts[inventory_hostname].swap | map(attribute='name') | join(', ') }}
      Timestamp: {{ ansible_date_time.iso8601 }}
    dest: /var/log/omnia_mounts.log
  delegate_to: "{{ item }}"
  loop: "{{ all_hostnames }}"
```

## Integration with Existing Roles

### Option 1: Extend nfs_client Role

```yaml
# roles/nfs_client/tasks/main.yml
---
- name: Include cloud-init mounts configuration
  include_tasks: cloud_init_mounts.yml
  when: use_cloud_init_mounts | default(false)

- name: Traditional NFS client setup
  include_tasks: traditional_nfs.yml
  when: not (use_cloud_init_mounts | default(false))
```

### Option 2: Create New storage_mounts Role

```yaml
# Create dedicated role for mount management
# Can be called from existing playbooks
- name: Configure storage mounts
  include_role:
    name: storage_mounts
  vars:
    storage_config_file: "{{ omnia_input_path }}/storage_config.yml"
    pxe_mapping_file: "{{ omnia_input_path }}/pxe_mapping_file.csv"
```

## Security Considerations

1. **Credential Management**: 
   - CIFS credentials stored in `/root/.smbcreds` with 0600 permissions
   - Use Ansible Vault for sensitive mount options

2. **Mount Options**:
   - Always use `nofail` to prevent boot failures
   - Use `_netdev` for network filesystems
   - Use `nosuid,nodev,noexec` where appropriate

3. **Validation**:
   - Validate all paths to prevent directory traversal
   - Sanitize user inputs from storage_config.yml
   - Check filesystem types against allowed list

4. **Permissions**:
   - Swap files created with 0600 permissions
   - Mount points created with appropriate ownership

## Testing Strategy

```yaml
# Test playbook
---
- name: Test storage mounts configuration
  hosts: localhost
  tasks:
    - name: Validate configuration syntax
      include_role:
        name: storage_mounts
        tasks_from: validate
    
    - name: Dry run - show what would be mounted
      include_role:
        name: storage_mounts
      vars:
        check_mode: true
    
    - name: Apply to single test host
      include_role:
        name: storage_mounts
      vars:
        limit_hosts: ["compute01"]
```

## Conclusion

This Ansible-based design provides a flexible, maintainable approach to managing storage mounts and swap configurations without requiring Python modules or controller access to storage systems. By leveraging Ansible's native capabilities (tasks, templates, filters, and delegation), the system can efficiently manage mounts across heterogeneous clusters while maintaining idempotency and providing clear audit trails.

The design supports both cloud-init and direct mount management approaches, allowing deployment flexibility based on environment requirements.
