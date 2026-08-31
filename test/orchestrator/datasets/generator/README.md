# Orchestrator Dataset Generator

This directory contains the dataset generator for orchestrator tests, following Pattern 2 (Jinja2 templates with profiles) to align with build_stream and image_build_manager modules.

## Structure

```
generator/
├── templates/
│   └── input/
│       ├── orchestrator_config.yml.j2
│       └── network_spec.yml.j2
├── profiles/
│   ├── defaults.yml
│   └── slurm_only.yml
├── generate_dataset.py
└── README.md
```

## Usage

### Generate a dataset

```bash
cd datasets/generator/
python generate_dataset.py <dataset_name> <profile>
```

### Examples

```bash
# Generate slurm_only dataset with slurm_only profile
python generate_dataset.py slurm_only slurm_only

# Generate data_set_01 dataset with defaults profile
python generate_dataset.py data_set_01 defaults

# Generate with CLI variable overrides
python generate_dataset.py my_custom defaults --var pxe_mapping_file_path=/path/to/mapping.csv

# Force overwrite existing dataset
python generate_dataset.py slurm_only slurm_only --force
```

### List available profiles

```bash
python generate_dataset.py --list-profiles
```

## Profiles

- **defaults**: Base profile with default orchestrator configuration
- **slurm_only**: SLURM-specific configuration with DCGM enabled

## Templates

- **orchestrator_config.yml.j2**: Main orchestrator configuration template
- **network_spec.yml.j2**: Network specification template

## Alignment

This generator follows the same pattern as:
- `test/build_stream/datasets/generator/`
- `test/image_build_manager/datasets/generator/`

## Regenerating Datasets

To regenerate an existing dataset:

```bash
cd datasets/generator/
python generate_dataset.py <dataset_name> <profile> --force
```

## Dataset Usage

After generating a dataset, update `test_config.yml`:

```yaml
dataset: "slurm_only"  # or "data_set_01"
```
