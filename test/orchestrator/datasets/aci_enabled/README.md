# aci_enabled dataset

Test dataset that enables the additional cloud-init feature for FVT testing.

## What it does

Overlays `orchestrator_config.yml` so that `additional_cloud_init_config_file`
points to `additional_cloud_init.yml`.  The included cloud-init configuration
creates verifiable artifacts on every provisioned node:

| Artifact | Source | Verification |
|----------|--------|-------------|
| `/etc/omnia/aci_common.conf` | `write_files` | File existence check |
| `/var/log/omnia_aci_common.log` | `runcmd` redirect | File existence check |

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

Edit `input/additional_cloud_init.yml` to add per-functional-group overrides.
Replace the example group name in the `groups:` section with a functional group
from your active `pxe_mapping_file.csv`.
