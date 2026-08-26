# Utils Domain -- Architecture

## System Context

```
  pxe_mapping_file.csv                                             failed_nodes.json
  set_pxe_boot_config.yml                                          utils_status.yml
  +---------------------+     +-------------------------------------+     +-----------+
  |                     |     |          Utils Domain                |     |           |
  |  User Input         |---->|                                     |---->| BuildStream|
  |  (config files)     |     |  setup -> precheck -> credentials   |     | GitLab    |
  |                     |     |         -> execute -> report        |     | (consumer)|
  +---------------------+     +-------------------------------------+     +-----------+
                                       |              |
                                  iDRAC API     Cloud-init Server
                                 (Redfish)      (phone-home)
```

## Execution Mode

**Bare-metal only.** Runs directly on RHEL host via `ansible-playbook`.
Tasks execute locally (`connection: local`) for credential collection and
configuration, then delegate to BMC hosts for PXE boot operations.

## Domain Components

### 1. PXE Boot Utility (`set_pxe_boot.yml`)

Sets PXE boot on Dell iDRAC nodes and triggers restart via Redfish API.
Optionally verifies cloud-init phone-home callbacks.

### 2. Log Collector (`collect.yml`)

Collects logs from K8s masters, workers, Slurm controllers, and nodes.
Bundles collected logs for support analysis.

### 3. Slurm Configuration Utility (`slurm_config_util.yml`)

Manages Slurm configuration backup, cleanup, and rollback operations.

### 4. ARM OS Installation (`install_os.yml`, `install_os_arm_node.yml`)

Installs RHEL on AArch64 nodes via iDRAC virtual media.

## Execution Flow (PXE Boot)

### Step 0: Setup (tag: always)

Role: `utils_setup`

- Load environment variables from `omnia.env`
- Set project directories and host vars
- Validate prerequisite files exist

### Step 1: Precheck (tag: precheck)

Role: `precheck_environment`

- Validate system environment via `validate_system_environment` module
- Check omnia.env is installed system-wide
- Cross-validate hostname, domain, admin IP

### Step 2: Credentials (tag: credentials)

Role: `collect_pxe_credentials`

- Prompt for BMC credentials (username/password)
- Store encrypted with Ansible Vault

### Step 3: PXE Boot (tag: pxe)

Roles: `idrac_pxe_boot`, `verify_phone_home`

- Set PXE boot source override via iDRAC Redfish API
- Restart servers (graceful or forced)
- Optionally wait for cloud-init phone-home callbacks

### Step 4: Report

Role: `utils_status_writer`

- Write `utils_status.yml` output file
- Write `failed_nodes.json` for nodes that failed PXE boot or phone-home

## Role Dependency Graph

```
utils_setup
       |
       +---> precheck_environment
       |
       +---> collect_pxe_credentials
       |           |
       +---> idrac_pxe_boot ---> verify_phone_home
       |
       +---> utils_status_writer
```

## Data Contract

### Inputs

| File | Source | Purpose |
|------|--------|---------|
| `set_pxe_boot_config.yml` | `input/` | PXE boot configuration |
| `set_pxe_boot_credentials.yml` | `input/` | BMC credentials (vault-encrypted) |
| `pxe_mapping_file.csv` | `input/project_default/` | Node BMC-to-admin IP mapping |
| Inventory (`.ini`) | User provided | BMC hosts to configure |

### Outputs

| File | Location | Purpose |
|------|----------|---------|
| `utils_status.yml` | `output/<project>/` | Domain execution status |
| `failed_nodes.json` | `output/<project>/` | Nodes that failed PXE boot or phone-home |

## Key Design Decisions

1. **Standalone domain** -- no dependency on other domains at code level
2. **Contract-based** -- reads config files, writes status files
3. **Inventory-driven** -- BMC hosts provided via Ansible inventory
4. **Idempotent credentials** -- prompts only if credentials are missing
5. **Phone-home optional** -- can be disabled via configuration
6. **BuildStream integration** -- writes `failed_nodes.json` for retry workflows
