# Utils Domain -- Input Contract

**Domain**: `utils` | **Collection**: `omnia.utils`

---

> **Note**: PXE boot input contracts (`set_pxe_boot_config.yml`, credentials, inventory)
> have been moved to the orchestrator domain. See `src/orchestrator/docs/` for details.

## 1. iso_config.yml (ARM Install)

**Purpose**: Configuration for AArch64 OS installation.

**Location**: `input/project_default/iso_config.yml`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `iso_source_path` | string | Yes | - | Path to source RHEL ISO |
| `iso_source_checksum` | string | No | `""` | SHA256 checksum for verification |
| `iso_target_directory` | string | No | `<OMNIA_DATA_PATH>/iso_output` | Output directory |
| `nfs_share_path` | string | No | Auto-detect | NFS share for iDRAC virtual media |
| `kickstart_template` | string | No | `rhel10` | Built-in kickstart template |
| `kickstart_file` | string | No | `""` | Custom kickstart file path |
| `force_reinstall` | bool | No | `false` | Reinstall even if node is reachable |

---

## 2. Environment Variables

**Purpose**: System-wide configuration from `omnia.env`.

**Location**: `/etc/omnia/omnia.env` (installed by `omnia.sh --setup-venv`)

| Variable | Required | Description |
|----------|----------|-------------|
| `OMNIA_DATA_PATH` | Yes | Base path for Omnia data (default: `/opt/omnia`) |
| `OMNIA_PROJECT_NAME` | No | Project name (default: `project_default`) |
| `SYSTEM_ADMIN_NIC_IPV4` | Yes | OIM admin network IP |
| `SYSTEM_HOSTNAME` | Yes | OIM short hostname |
| `SYSTEM_DOMAIN_NAME` | No | Domain name |


