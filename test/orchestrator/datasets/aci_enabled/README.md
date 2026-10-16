# aci_enabled dataset

Test dataset that provides the `additional_cloud_init.yml` input for FVT
testing. The cloud-init configuration creates verifiable artifacts on
provisioned nodes.

## What it does

Supplies `additional_cloud_init.yml` which the dataset sync copies into the
active project's input directory on the execution OIM. The live
`orchestrator_config.yml` on the OIM must already have
`additional_cloud_init_config_file` set to `"additional_cloud_init.yml"`.

| Artifact | Scope | Source | Verification |
|----------|-------|--------|-------------|
| `/etc/omnia/aci_common.conf` | All nodes | `write_files` | File existence check |
| `/var/log/omnia_aci_common.log` | All nodes | `runcmd` redirect | File existence check |
| `/var/log/omnia_aci_pkg_check.log` | All nodes | `rpm -q bash` redirect | Package integration check |
| `/etc/omnia/aci_slurm_node.conf` | `slurm_node_rhel_10_0_x86_64` | `write_files` | Per-FG file check |
| `/var/log/omnia_aci_slurm_node.log` | `slurm_node_rhel_10_0_x86_64` | `runcmd` redirect | Per-FG file check |
| `/etc/omnia/aci_slurm_control.conf` | `slurm_control_node_rhel_10_0_x86_64` | `write_files` | Per-FG file check |
| `/var/log/omnia_aci_slurm_control.log` | `slurm_control_node_rhel_10_0_x86_64` | `runcmd` redirect | Per-FG file check |

## Usage

```yaml
# test_config.yml
dataset: "aci_enabled"
sync_orchestrator_input: true
validate_additional_cloud_init: true
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

Edit `input/additional_cloud_init.yml` to adjust per-functional-group overrides.
The shipped `groups` section includes `slurm_node_rhel_10_0_x86_64` and
`slurm_control_node_rhel_10_0_x86_64`. Replace or extend these with functional
groups from your active `pxe_mapping_file.csv`.
