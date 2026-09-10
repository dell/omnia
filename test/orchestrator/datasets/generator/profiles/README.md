# Orchestrator Dataset Generator Profiles

**IMPORTANT**: Per the Official Omnia Test Automation Design Document (v2.0), datasets MUST be created via the generator tool, NEVER manually.

This directory contains YAML profile definitions used by the dataset generator to create test datasets.

## Profile System

The generator uses a profile-based system for dataset generation:

1. **`defaults.yml`** - Base profile with default orchestrator configuration
2. **Variant profiles** - Deployment-specific configurations (k8s_only, slurm_only, k8s_and_slurm)

Profiles control:
- Template variable values (when rendering from templates)
- File filtering (when using `--from-src`)
- Sample directory inclusion (repo_manager_output, image_build_manager_output)

## Available Profiles

### 1. k8s_only.yml
Kubernetes-only deployment configuration.

**Configuration:**
- dcgm_enabled: false (no GPU monitoring for K8s-only)

**File Filter (when using --from-src):**
- Input files: All 9 input files from src/orchestrator/input/
- Sample directories: repo_manager_output, image_build_manager_output

**Functional Groups:**
- `service_kube_control_plane` - Kubernetes control plane nodes
- `service_kube_node` - Kubernetes worker nodes

### 2. slurm_only.yml
Slurm-only deployment configuration.

**Configuration:**
- dcgm_enabled: true (GPU monitoring for Slurm)

**File Filter (when using --from-src):**
- Input files: All 9 input files from src/orchestrator/input/
- Sample directories: repo_manager_output, image_build_manager_output

**Functional Groups:**
- `slurm_control_node` - Slurm controller nodes
- `slurm_node` - Slurm compute nodes
- `login_node` - Login nodes

### 3. k8s_and_slurm.yml
Combined Kubernetes + Slurm deployment configuration.

**Configuration:**
- dcgm_enabled: true (GPU monitoring for combined deployments)

**File Filter (when using --from-src):**
- Input files: All 9 input files from src/orchestrator/input/
- Sample directories: repo_manager_output, image_build_manager_output

**Functional Groups:**
- All K8s functional groups
- All Slurm functional groups

### 4. defaults.yml
Base profile with default orchestrator configuration.

**Configuration:**
- dcgm_enabled: true (default GPU monitoring)

**File Filter (when using --from-src):**
- No filtering - copies all files from src/orchestrator/

## Creating Datasets

### Generate from Source Files (Recommended)

```bash
cd datasets/generator

# Create a K8s-only dataset with profile filtering
./generate_dataset.py k8s_dataset_01 k8s_only --from-src

# Create a Slurm-only dataset with profile filtering
./generate_dataset.py slurm_dataset_01 slurm_only --from-src

# Create a combined dataset with profile filtering
./generate_dataset.py combined_dataset_01 k8s_and_slurm --from-src

# Create with default profile (no filtering)
./generate_dataset.py default_dataset_01 defaults --from-src
```

### Generate from Templates

```bash
cd datasets/generator

# Generate with profile-based template rendering
./generate_dataset.py k8s_dataset_01 k8s_only

# Generate with CLI variable overrides
./generate_dataset.py my_custom defaults --var pxe_mapping_file_path=/path/to/mapping.csv
```

### Check and Dry-Run

```bash
cd datasets/generator

# Check if existing dataset is current
./generate_dataset.py k8s_dataset_01 k8s_only --check

# Test generation without publishing
./generate_dataset.py k8s_dataset_01 k8s_only --dry-run
```

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

## Profile Structure

Each profile YAML file contains:

```yaml
# Template variables
dcgm_enabled: false

# File filter configuration (for --from-src mode)
include_files:
  input:
    - additional_cloud_init.yml
    - high_availability_config.yml
    - network_spec.yml
    - omnia_config.yml
    - orchestrator_config.yml
    - pxe_mapping_file.csv
    - security_config.yml
    - set_pxe_boot_config.yml
    - storage_config.yml
  samples:
    - repo_manager_output
    - image_build_manager_output
```

## Input Files

The generator processes these input files from `src/orchestrator/input/`:

1. `additional_cloud_init.yml` - Additional cloud-init configuration
2. `high_availability_config.yml` - HA configuration for K8s
3. `network_spec.yml` - Network specification
4. `omnia_config.yml` - Omnia configuration (Slurm + K8s clusters)
5. `orchestrator_config.yml` - Orchestrator configuration
6. `pxe_mapping_file.csv` - Node-to-FG mapping
7. `security_config.yml` - Security configuration
8. `set_pxe_boot_config.yml` - PXE boot configuration
9. `storage_config.yml` - Storage configuration

## Sample Directories

The generator copies these sample directories from `src/orchestrator/samples/`:

1. `repo_manager_output/` - Repository manager output (repo_status.yml)
2. `image_build_manager_output/` - Image build manager output (build_status.yml)

This ensures datasets follow the exact format as the source files, matching the image_build_manager pattern.

## CLI Options

| Option | Description |
|--------|-------------|
| `--from-src` | Copy files directly from src/ with profile filtering |
| `--check` | Check if dataset is current (compare with staged output) |
| `--dry-run` | Generate staging output without publishing |
| `--force` | Overwrite existing dataset directory |
| `--var KEY=VALUE` | Override a template variable (repeatable) |
| `--list-profiles` | List available profiles and exit |

## See Also

- **Generator Documentation**: `../README.md`
- **Dataset Documentation**: `../../README.md`
- **Alignment Plan**: `../../ALIGNMENT_PLAN.md`
- **Compliance Summary**: `../../COMPLIANCE_SUMMARY.md`
