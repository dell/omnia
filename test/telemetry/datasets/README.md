# Telemetry Test Datasets

Test input datasets for the telemetry FVT module.

## Generating Datasets

Use the generator tool to create datasets:

```bash
cd generator/
python generate_dataset.py <name> <profile>
```

See `generator/README.md` for full usage.

## Dataset Structure

```
data_set_01/
└── input/
    ├── telemetry_config.yml
    ├── telemetry_storage_config.yml
    └── telemetry_packages.yml
```
