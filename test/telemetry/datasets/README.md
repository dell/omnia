# Datasets

Test input configuration for the `telemetry` automation framework.

## Default Mode (Recommended)

By default (`dataset: ""` in `test_config.yml`), no generated dataset folder is
needed. The target keeps using its existing runtime files. If sync is enabled,
the corresponding local sync source comes directly from `src/`:

| File | Source |
|------|--------|
| `telemetry_config.yml` | `src/telemetry/input/` |
| `telemetry_storage_config.yml` | `src/telemetry/input/` |
| `telemetry_packages.yml` | `src/telemetry/input/` |

With sync disabled, nothing is copied and execution reads the files already
present on the target under `$OMNIA_DATA_PATH`.

## Custom Datasets

Set `dataset: "my_ds"` in `test_config.yml` to select a custom local sync
source from `datasets/<name>/`. Generate one with the source-first generator:

```bash
cd datasets/generator/
./generate_dataset.py profiles
./generate_dataset.py profiles defaults
./generate_dataset.py create my_ds --profile defaults --dry-run
./generate_dataset.py create my_ds --profile defaults
```

The ten canonical profiles select supported source combinations and deployment modes:

| Profile | Use Case |
|---------|----------|
| `idrac_powerscale` | iDRAC + PowerScale |
| `idrac_ldms_powerscale` | iDRAC + LDMS + PowerScale |
| `idrac_ldms` | iDRAC + LDMS (HPC cluster baseline) |
| `idrac_ome_ufm` | iDRAC + OME + UFM |
| `idrac_powerscale_vast` | iDRAC + PowerScale + VAST |
| `ldms_only` | LDMS only (compute-node metrics) |
| `powerscale_only` | PowerScale metrics and logs only |
| `defaults` | Canonical source defaults (iDRAC, LDMS, PowerScale, and OME) |
| `online_mode` | Canonical source defaults with online installation |
| `offline_mode` | Canonical source defaults with offline installation |

SFM is not configured under `telemetry_sources`. It connects externally to the
VictoriaMetrics remote-write endpoint exposed by the telemetry deployment.

**Important: Offline mode requires repo_url configuration**

When using the `offline_mode` profile, you **must** configure `repo_url` in the generated `telemetry_packages.yml`:

```bash
# Generate the dataset
cd datasets/generator/
./generate_dataset.py create my_offline --profile offline_mode

# Edit the generated telemetry_packages.yml
nano ../my_offline/input/telemetry_packages.yml
```

Set repo_url to your Pulp repository base URL

# Example Format: https://<ip_or_hostname>:<port>/pulp/content/opt/omnia/offline_repo/cluster/<arch>/<os>/<version>

The `repo_url` is used to construct all offline package URLs:
- Helm charts: `<repo_url>/tarball/<package>/<filename>`
- Git repos: `<repo_url>/git/<package>/<filename>`
- Pip modules: `<repo_url>/pip_module/<package>==<version>/`

Leave `repo_url: ""` for `online_mode` (not needed).

For a quick PowerScale-only dataset:

```bash
./generate_dataset.py create my_powerscale --profile powerscale_only
```

See [`generator/README.md`](generator/README.md) for full usage.

### Custom Dataset Structure

```
datasets/<name>/
  input/
    telemetry_config.yml
    telemetry_storage_config.yml
    telemetry_packages.yml
  dataset_manifest.yml
  README.md
```

Datasets never contain credentials. Appliance credentials (OME, SFM, UFM,
VAST) are stored in `test_creds.yml` and auto-encrypted with Ansible Vault.

## Switching Datasets

### Method 1: Edit `test_config.yml` (persistent)
```yaml
dataset: "my_custom_ds"    # Use custom dataset
dataset: ""                # Use src/ only as an optional sync source
sync_telemetry_input: true # Enable sync to push files to target
```

Then run normally:
```bash
./run_validation.sh fvt_telemetry deploy verify
```

### Method 2: Environment variables (one-off)
Override dataset and/or sync settings without editing the config file:

```bash
# Override dataset only (sync respects test_config.yml setting)
OMNIA_DATASET_OVERRIDE=my_custom_ds \
  ./run_validation.sh fvt_telemetry deploy verify

# Override both dataset and sync
OMNIA_DATASET_OVERRIDE=my_custom_ds \
OMNIA_SYNC_INPUT_OVERRIDE=true \
  ./run_validation.sh fvt_telemetry deploy verify

# Override sync only (dataset from test_config.yml)
OMNIA_SYNC_INPUT_OVERRIDE=true \
  ./run_validation.sh fvt_telemetry deploy verify
```

**Priority:**
- `OMNIA_DATASET_OVERRIDE` takes priority over `test_config.yml` dataset
- `OMNIA_SYNC_INPUT_OVERRIDE` takes priority over `test_config.yml` sync_telemetry_input

## Sync Behavior

| Setting | What gets synced |
|---------|------------------|
| `sync_telemetry_input: true`, named dataset | `datasets/<name>/input/` → target input path |
| `sync_telemetry_input: true`, empty dataset | `src/telemetry/input/` → target input path |
| `sync_telemetry_input: false` | Nothing is synced; target keeps existing files |

The framework reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the
target server to resolve sync destinations.
