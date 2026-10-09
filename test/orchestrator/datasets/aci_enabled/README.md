# aci_enabled dataset

Test dataset that enables the additional cloud-init feature for FVT testing.

## What it does

Overlays `orchestrator_config.yml` so that `additional_cloud_init_config_file`
points to `additional_cloud_init.yml`.  All other orchestrator config variables
retain their shipped defaults.  The included cloud-init configuration creates
verifiable artifacts on provisioned nodes:

| Scope | Artifact | Source | Verification |
|-------|----------|--------|-------------|
| Common (all nodes) | `/etc/omnia/aci_common.conf` | `write_files` | File existence check |
| Common (all nodes) | `/var/log/omnia_aci_common.log` | `runcmd` redirect | File existence check |
| `slurm_node_rhel_10_0_x86_64` | `/etc/omnia/aci_slurm_node.conf` | `write_files` | File existence on matching nodes |
| `slurm_node_rhel_10_0_x86_64` | `/var/log/omnia_aci_slurm_node.log` | `runcmd` redirect | File existence on matching nodes |
| `slurm_control_node_rhel_10_0_x86_64` | `/etc/omnia/aci_slurm_control.conf` | `write_files` | File existence on matching nodes |
| `slurm_control_node_rhel_10_0_x86_64` | `/var/log/omnia_aci_slurm_control.log` | `runcmd` redirect | File existence on matching nodes |

## Usage

```yaml
# test_config.yml
dataset: "aci_enabled"
sync_orchestrator_input: true
```

Or per-scenario in `test_run_config.yml`:

```yaml
fvt_orchestrator:
  pxeboot:
    dataset: "aci_enabled"
    sync_input: true
    suite: "additional_cloud_init"
```

Then run:

```bash
./run_validation.sh fvt_orchestrator pxeboot verify --suite additional_cloud_init
```

## Customization

Edit `input/additional_cloud_init.yml` to match your environment:

- Replace the functional group names (`slurm_node_rhel_10_0_x86_64`,
  `slurm_control_node_rhel_10_0_x86_64`) with the actual functional group
  names from your active `pxe_mapping_file.csv`.
- Add more groups as needed for additional functional groups.
- Modify `write_files` paths and `runcmd` entries to create different
  verifiable artifacts.
