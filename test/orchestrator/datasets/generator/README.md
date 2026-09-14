# Orchestrator Dataset Generator

This directory contains the dataset generator for orchestrator tests, following the Official Omnia Test Automation Design Document (v2.0) and aligned with the image_build_manager module.

## Structure

```
generator/
├── templates/
│   └── input/
│       ├── additional_cloud_init.yml.j2
│       ├── high_availability_config.yml.j2
│       ├── network_spec.yml.j2
│       ├── omnia_config.yml.j2
│       ├── orchestrator_config.yml.j2
�       ├── pxe_mapping_file.csv.j2
│       ├── security_config.yml.j2
│       ├── set_pxe_boot_config.yml.j2
│       └── storage_config.yml.j2
├── profiles/
│   ├── defaults.yml
│   ├── k8s_only.yml
│   ├── slurm_only.yml
│   ├── k8s_and_slurm.yml
│   └── README.md
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

#### Generate from Source Files (Recommended)

```bash
# Generate K8s-only dataset
python generate_dataset.py my_k8s_dataset k8s_only --from-src

# Generate Slurm-only dataset
python generate_dataset.py my_slurm_dataset slurm_only --from-src

# Generate combined K8s + Slurm dataset
python generate_dataset.py my_combined_dataset k8s_and_slurm --from-src

# Generate with default profile (no filtering)
python generate_dataset.py my_dataset defaults --from-src
```

#### Generate from Templates

```bash
# Generate with profile-based template rendering
python generate_dataset.py my_dataset k8s_only

# Generate with CLI variable overrides
python generate_dataset.py my_custom defaults --var pxe_mapping_file_path=/path/to/mapping.csv
```

#### Check and Dry-Run

```bash
# Check if existing dataset is current
python generate_dataset.py my_k8s_dataset k8s_only --check

# Test generation without publishing
python generate_dataset.py my_k8s_dataset k8s_only --dry-run
```

#### Force Overwrite

```bash
# Force overwrite existing dataset
python generate_dataset.py my_k8s_dataset k8s_only --from-src --force
```

### List Available Profiles

```bash
python generate_dataset.py --list-profiles
```

## CLI Options

| Option | Description |
|--------|-------------|
| `dataset_name` | Name of the dataset directory to create |
| `profile` | Profile name: defaults, k8s_only, slurm_only, k8s_and_slurm, or custom |
| `--var KEY=VALUE` | Override a template variable (repeatable) |
| `--list-profiles` | List available profiles and exit |
| `--force` | Overwrite existing dataset directory |
| `--from-src` | Copy files directly from src/ instead of rendering templates |
| `--check` | Check if dataset is current (compare with staged output) |
| `--dry-run` | Generate staging output without publishing to datasets/ |

## Profiles

### Available Profiles

- **defaults**: Base profile with default orchestrator configuration
- **k8s_only**: Kubernetes-only deployment configuration
  - dcgm_enabled: false
  - Includes: All 9 input files + repo_manager_output + image_build_manager_output
- **slurm_only**: Slurm-only deployment configuration
  - dcgm_enabled: true
  - Includes: All 9 input files + repo_manager_output + image_build_manager_output
- **k8s_and_slurm**: Combined Kubernetes + Slurm deployment configuration
  - dcgm_enabled: true
  - Includes: All 9 input files + repo_manager_output + image_build_manager_output

### Profile-Based File Filtering

When using `--from-src`, profiles control which files are included:

- **k8s_only**: Filters to include specific input files and sample directories
- **slurm_only**: Filters to include specific input files and sample directories
- **k8s_and_slurm**: Filters to include specific input files and sample directories
- **defaults**: No filtering - copies all files from src/

Each profile defines:
- `include_files.input`: List of input files to include
- `include_files.samples`: List of sample directories to include

## Templates

All input files from `src/orchestrator/input/` are available as Jinja2 templates:

- **additional_cloud_init.yml.j2**: Additional cloud-init configuration
- **high_availability_config.yml.j2**: High availability configuration for K8s
- **network_spec.yml.j2**: Network specification
- **omnia_config.yml.j2**: Omnia configuration (Slurm + K8s clusters)
- **orchestrator_config.yml.j2**: Orchestrator configuration
- **pxe_mapping_file.csv.j2**: Node-to-FG mapping
- **security_config.yml.j2**: Security configuration
- **set_pxe_boot_config.yml.j2**: PXE boot configuration
- **storage_config.yml.j2**: Storage configuration

## Dataset Structure

Generated datasets include:

```
<dataset_name>/
├── input/                          # 9 input files from src/orchestrator/input/
│   ├── additional_cloud_init.yml
│   ├── high_availability_config.yml
│   ├── network_spec.yml
│   ├── omnia_config.yml
│   ├── orchestrator_config.yml
│   ├── pxe_mapping_file.csv
│   ├── security_config.yml
│   ├── set_pxe_boot_config.yml
│   └── storage_config.yml
├── repo_manager_output/             # From src/orchestrator/samples/repo_manager_output/
│   └── repo_status.yml
├── image_build_manager_output/     # From src/orchestrator/samples/image_build_manager_output/
│   └── build_status.yml
└── README.md                         # Auto-generated documentation
```

## Alignment

This generator follows the same pattern as:
- `test/image_build_manager/datasets/generator/` (reference implementation)
- Official Omnia Test Automation Design Document (v2.0)

## Key Features

### Staging Directory
- Uses temporary staging directory for atomic operations
- Generates to staging first, then publishes to final location
- Automatically cleans up staging directory

### Profile-Based Filtering
- Profiles control which files are included when using `--from-src`
- Supports input file filtering and sample directory selection
- Falls back to copying all files if no filter specified

### Check Mode
- Compare existing dataset with newly generated staging output
- Detects new, modified, and deleted files
- Returns error if dataset is stale

### Dry-Run Mode
- Generate staging output without publishing
- Useful for testing before actual generation
- Shows staging output path for inspection

## Regenerating Datasets

To regenerate an existing dataset:

```bash
cd datasets/generator/
python generate_dataset.py <dataset_name> <profile> --force
```

## Dataset Usage

After generating a dataset, update `test_config.yml`:

```yaml
dataset: "my_k8s_dataset"
sync_orchestrator_input: true
```

Or override at runtime:

```bash
export OMNIA_DATASET_OVERRIDE="my_slurm_dataset"
pytest fvt/
```

## See Also

- **Profile Documentation**: `profiles/README.md`
- **Dataset Documentation**: `../README.md`
- **Alignment Plan**: `../../ALIGNMENT_PLAN.md`
- **Compliance Summary**: `../../COMPLIANCE_SUMMARY.md`
