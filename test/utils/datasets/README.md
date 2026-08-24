# Utils Domain — Test Datasets

This directory contains test datasets for the utils domain FVT.

## Structure

```
datasets/
├── generator/           # Dataset generator tool
│   ├── generate_dataset.py
│   ├── profiles/        # Variable profiles
│   └── templates/       # Jinja2 templates
├── data_set_01/         # Generated dataset (example)
│   ├── input/
│   └── README.md
└── README.md            # This file
```

## Creating Datasets

Use the generator tool to create new datasets:

```bash
cd generator/

# From template with default profile
python generate_dataset.py data_set_01 defaults

# From src/utils/input/
python generate_dataset.py data_set_02 --from-src
```

## Using Datasets

Set the `dataset` field in `test_config.yml`:

```yaml
dataset: "data_set_01"
```

When `dataset` is empty, tests use `src/utils/input/` directly.

## Dataset Contents

Each dataset contains:

- `input/` — Input files synced to target
  - `collect_pxe.yml` — Log collector node inventory
  - `set_pxe_boot_config.yml` — PXE boot configuration
  - `set_pxe_boot.ini` — BMC inventory
  - `set_pxe_boot_credentials.yml` — BMC credentials
- `README.md` — Auto-generated documentation
