# Utils Domain — Test Datasets

This directory contains test datasets for the utils domain FVT.

## Structure

```
datasets/
├── generator/           # Dataset generator tool
│   ├── generate_dataset.py
│   ├── profiles/        # Variable profiles
│   │   ├── defaults.yml
│   │   └── example_install_os.yml
│   └── templates/       # Jinja2 templates
│       └── input/
│           ├── collect_pxe.yml.j2
│           └── install_os_config.yml.j2
├── data_set_01/         # Generated dataset (example)
│   ├── input/
│   └── README.md
└── README.md            # This file
```

## Creating Datasets

Use the generator tool to create new datasets:

```bash
cd generator/

# From template with default profile
python generate_dataset.py --name my_dataset

# From template with custom profile
python generate_dataset.py --name my_dataset --profile example_install_os.yml
```

## Using Datasets

Set the `dataset` field in `test_config.yml`:

```yaml
dataset: "my_dataset"
sync_utils_input: true
oim_server_ip: "10.0.0.100"
```

When `dataset` is empty, tests use `src/utils/input/` directly.

## Dataset Contents

Each dataset contains:

- `input/` — Input files synced to target
  - `collect_pxe.yml` — Log collector node inventory
  - `install_os_config.yml` — Install OS configuration
- `README.md` — Auto-generated documentation

## Profile Variables

### Log Collector Configuration

- `service_kube_control_plane_x86_64` - List of K8s control plane IPs
- `service_kube_node_x86_64` - List of K8s worker node IPs
- `slurm_control_node_x86_64` - List of Slurm control node IPs
- `slurm_node_x86_64` - List of Slurm compute node IPs (x86_64)
- `slurm_node_aarch64` - List of Slurm compute node IPs (aarch64)
- `login_node_x86_64` - List of login node IPs
- `login_compiler_node_aarch64` - List of login compiler node IPs

### Install OS Configuration

- `source_iso_path` - Path to source RHEL ISO
- `source_iso_checksum` - SHA-256 checksum for verification
- `custom_iso_path` - NFS path for custom ISO
- `kickstart_delivery_method` - embedded or nfs
- `kickstart_file` - User-provided kickstart file (optional)
- `kickstart_template` - Template name (rhel10)
- `target_bmc_ip` - iDRAC/BMC IP address
- `target_hostname` - Hostname for installed OS
- `target_admin_ip` - Admin network IP
- `target_architecture` - x86_64 or aarch64
- `network_device` - Network device name
- `netmask` - Network netmask
- `gateway` - Network gateway
- `dns_server` - DNS server
- `install_disk` - Target install disk
- `timezone` - Timezone for installed OS
- `rebuild_iso` - Force rebuild if ISO exists
- `force_reinstall` - Force reinstall if target reachable
- `ssh_verify_enabled` - Enable SSH verification after install
- `ssh_verify_retries` - SSH verification retry count
- `ssh_verify_delay` - SSH verification delay
