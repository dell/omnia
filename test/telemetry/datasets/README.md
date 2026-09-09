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

### Edit `test_config.yml`
```yaml
dataset: "my_custom_ds"    # Use custom dataset
dataset: ""                # Use src/ only as an optional sync source
```

### Environment variable (one-off)
```bash
OMNIA_DATASET_OVERRIDE=my_custom_ds \
  ./run_validation.sh fvt_telemetry deploy verify
```

`OMNIA_DATASET_OVERRIDE` takes priority over the `test_config.yml` default.

## Sync Behavior

| Setting | What gets synced |
|---------|------------------|
| `sync_telemetry_input: true`, named dataset | `datasets/<name>/input/` -> target input path |
| `sync_telemetry_input: true`, empty dataset | `src/telemetry/input/` -> target input path |

The framework reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the
target server to resolve sync destinations.
