# Utils Domain -- Architecture

## System Context

```
  +---------------------+     +-------------------------------------+     +-----------+
  |                     |     |          Utils Domain                |     |           |
  |  User Input         |---->|                                     |---->| Output    |
  |  (config files)     |     |  setup -> precheck -> execute       |     | (logs,    |
  |                     |     |                                     |     |  status)  |
  +---------------------+     +-------------------------------------+     +-----------+
```

> **Note**: PXE boot utility (`set_pxe_boot.yml`) has been moved to the
> orchestrator domain at `src/orchestrator/playbooks/setpxe/set_pxe_boot.yml`.

## Execution Mode

**Bare-metal only.** Runs directly on RHEL host via `ansible-playbook`.

## Domain Components

### 1. Log Collector (`collect.yml`)

Collects logs from K8s masters, workers, Slurm controllers, and nodes.
Bundles collected logs for support analysis.

### 2. Slurm Configuration Utility (`slurm_config_util.yml`)

Manages Slurm configuration backup, cleanup, and rollback operations.

### 3. ARM OS Installation (`install_os.yml`, `install_os_arm_node.yml`)

Installs RHEL on AArch64 nodes via iDRAC virtual media.

## Key Design Decisions

1. **Standalone domain** -- no dependency on other domains at code level
2. **Contract-based** -- reads config files, writes status files
3. **PXE boot moved** -- PXE boot utility now lives in orchestrator domain
