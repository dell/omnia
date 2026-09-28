# Orchestrator Test Datasets

This directory contains test datasets for orchestrator validation.

## Dataset Generation

**IMPORTANT**: Per the Official Omnia Test Automation Design Document (v2.0), datasets MUST be created via the generator tool in `datasets/generator/`, NEVER manually.

## Creating Datasets

Use the dataset generator CLI:

```bash
cd datasets/generator

# List available profiles
./generate_dataset.py --list-profiles

# Create a K8s-only dataset
./generate_dataset.py k8s_dataset_01 k8s_only --from-src

# Create a Slurm-only dataset
./generate_dataset.py slurm_dataset_01 slurm_only --from-src

# Create a combined dataset
./generate_dataset.py combined_dataset_01 k8s_and_slurm --from-src
```

## Available Profiles

- **defaults** - Base profile (common settings)
- **k8s_only** - Kubernetes-only deployment (dcgm_enabled=false)
- **slurm_only** - Slurm-only deployment (src format)
- **k8s_and_slurm** - Combined Kubernetes + Slurm (dcgm_enabled=true)

## Using Datasets

Configure in `test_config.yml`:

```yaml
dataset: "k8s_dataset_01"
sync_orchestrator_input: true
```

Or override at runtime:

```bash
export OMNIA_DATASET_OVERRIDE="slurm_dataset_01"
pytest fvt/
```

## Dataset Structure

Each generated dataset contains:
```
<dataset_name>/
├── input/
│   ├── additional_cloud_init.yml
│   ├── high_availability_config.yml
│   ├── network_spec.yml
│   ├── omnia_config.yml
│   ├── orchestrator_config.yml
│   ├── pxe_mapping_file.csv
│   ├── security_config.yml
│   ├── set_pxe_boot_config.yml
│   └── storage_config.yml
└── README.md
```

All input files are copied directly from `src/orchestrator/input/` to ensure they match the exact format used in production.
