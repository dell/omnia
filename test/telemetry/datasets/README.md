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

The four canonical profiles select different source/sink combinations:

| Profile | Use Case |
|---------|----------|
| `defaults` | All sources and sinks enabled |
| `idrac_only` | iDRAC only (minimal deployment) |
| `sinks_only` | No sources; sink infrastructure testing |
| `minimal` | Everything disabled; validation-only |

For a quick iDRAC-only dataset:

```bash
./generate_dataset.py create my_idrac --profile idrac_only
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
