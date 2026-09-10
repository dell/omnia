# Datasets

Test input configuration for the `discovery` automation framework.

## Default Mode (Recommended)

By default (`dataset: ""` in `test_config.yml`), no generated dataset folder is
needed. The target keeps using its existing runtime files. If a sync option is
enabled, the corresponding local sync source comes directly from `src/`:

| File | Source |
|------|--------|
| `discovery_config.yml` | `src/discovery/input/` |
| `network_spec.yml` | `src/discovery/input/` |

With both sync flags disabled, nothing is copied and execution reads the files
already present on the target under `$OMNIA_DATA_PATH`.

## Custom Datasets

Set `dataset: "my_ds"` in `test_config.yml` to select a custom local sync
source from `datasets/<name>/`. Generate one with the source-first generator:

```bash
cd datasets/generator/
./generate_dataset.py profiles
./generate_dataset.py profiles defaults
./generate_dataset.py create my_ds \
  --profile defaults --dry-run
./generate_dataset.py create my_ds \
  --profile defaults
```

The `defaults` profile contains standard OME discovery configuration parameters.
Custom profiles can override OME IP, network settings, and other parameters.

Generated YAML retains applicable source headings and guidance. Environment-specific
dummy values have inline `# REPLACE WITH REAL VALUE` guidance; the dataset README
repeats the same checklist.

Enable `sync_discovery_input` when the selected files must be copied to the
execution target. Setting `dataset` alone does not replace files that already
exist on the target.

See [`generator/README.md`](generator/README.md) for full usage.

### Custom Dataset Structure

```
datasets/<name>/
  input/
    discovery_config.yml
    network_spec.yml
  dataset_manifest.yml
  README.md
```

Datasets never contain credentials. From `test/discovery` on the execution OIM,
create the separate encrypted runtime pair with `./setup_env.sh --set-domain-creds`.
The framework never transfers that YAML, its vault key, or backups. For remote
execution, run the command on the target OIM.

## Switching Datasets

### Edit `test_config.yml`
```yaml
dataset: "my_custom_ds"    # Use custom dataset
dataset: ""                # Use src/ only as an optional sync source
```

### Per-scenario override in `test_run_config.yml`
```yaml
fvt_discovery:
  execute:
    dataset: "my_custom_ds"
    sync_input: true
```

### Environment variable (one-off)
```bash
OMNIA_DATASET_OVERRIDE=my_custom_ds \
  ./run_validation.sh discovery execute verify
```

For a direct invocation, `OMNIA_DATASET_OVERRIDE` takes priority over the
`test_config.yml` default. For a batch run, the priority is top-level
`dataset_override`, per-FVT `dataset`, the inherited environment override, and
then the `test_config.yml` default.

## Sync Behavior

| Setting | What gets synced |
|---------|------------------|
| `sync_discovery_input: true`, named dataset | Only `datasets/<name>/input/` → execution OIM; credential artifacts are excluded |
| `sync_discovery_input: true`, empty dataset | Canonical `src/discovery/input/` → execution OIM; credential artifacts are excluded |

The framework reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME` from the
target server to resolve sync destinations.
