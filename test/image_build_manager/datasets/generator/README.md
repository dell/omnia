# Dataset Generator

Generates test dataset directories from **Jinja2 templates** and **YAML profiles**.
Eliminates duplication — shared values (base packages, functional groups, build
settings) are defined once in `defaults.yml` and reused across all datasets.

Source of truth for templates: `src/image_build_manager/input/` and
`src/image_build_manager/samples/repo_manager_output/`.

---

## Quick Start

```bash
cd test/image_build_manager/datasets/generator/

# Generate dataset with offline (Pulp) repos (default profile)
python generate_dataset.py my_offline_ds defaults

# Generate dataset with internet (CentOS Stream) repos
python generate_dataset.py my_internet_ds internet

# Override specific variables
python generate_dataset.py my_custom defaults --var s3_provider=powerscale

# Copy files directly from src/ (no templating, exact src/ content)
python generate_dataset.py my_src_ds --from-src
python generate_dataset.py my_src_ds --from-src --repo-variant internet

# List available profiles
python generate_dataset.py --list-profiles
```

---

## Architecture

```
generator/
├── generate_dataset.py          # CLI tool — renders templates into datasets
├── README.md                    # This file
├── profiles/                    # Variable profiles (YAML)
│   ├── defaults.yml             # Base profile — offline/Pulp repos (all values)
│   └── internet.yml             # Override: public CentOS Stream / EPEL repos
└── templates/                   # Jinja2 templates
    ├── input/
    │   ├── image_build_config.yml.j2
    │   ├── image_build_credentials.yml.j2
    │   └── package_groups.yml.j2
    └── repo_manager_output/
        ├── repo_status.yml.j2
        └── functional_group_packages.yml.j2
```

### How It Works

1. **`defaults.yml`** — contains all shared values (packages, build settings,
   offline repo definitions). This is the base profile.
2. **Profile overrides** (e.g., `internet.yml`) — override only keys that differ.
3. **CLI `--var` flags** — override individual values at generation time.
4. **Jinja2 templates** — reference these variables and render into YAML files.

**Merge order**: `defaults.yml` → `<profile>.yml` → `--var` overrides

---

## Profiles

| Profile | Repo Type | Description |
|---------|-----------|-------------|
| `defaults` | `offline` | Pulp-based repos with `{{ admin_nic_ip }}` placeholders |
| `internet` | `internet` | Public CentOS Stream + EPEL URLs (no Pulp needed) |

### Creating a Custom Profile

```bash
cp profiles/internet.yml profiles/my_profile.yml
vi profiles/my_profile.yml   # Only override what differs
```

---

## Parameters

### image_build_config.yml

| Variable | Default | Description |
|----------|---------|-------------|
| `repo_manager_output_path` | `/opt/omnia/repo_manager/output/project_default/repo_status.yml` | Path to repo_status.yml |
| `s3_provider` | `minio` | S3 backend: `minio` or `powerscale` |
| `s3_endpoint_url` | `""` | S3 endpoint (required for powerscale) |
| `image_build_type` | `image-builder` | Builder: `image-builder` or `image-thrillhouse` |
| `build_image_max_parallel` | `0` | Max concurrent builds (0 = unlimited) |
| `build_image_build_timeout` | `7200` | Build timeout in seconds |
| `build_image_force_rebuild` | `false` | Bypass package hash cache |
| `build_image_backup_s3_images` | `false` | Backup existing S3 artifacts before rebuild |
| `functional_groups_source` | `catalog` | Group source: `config` or `catalog` |
| `aarch64_inventory_host_ip` | `""` | ARM build host IP (empty = skip aarch64) |
| `aarch64_ssh_user` | `root` | SSH user for ARM build host |

### image_build_credentials.yml

| Variable | Default | Description |
|----------|---------|-------------|
| `s3_access_id` | `""` | S3 access key ID |
| `s3_secret_key` | `""` | S3 secret key |
| `aarch64_ssh_password` | `""` | SSH password for ARM build host |

### package_groups.yml

| Variable | Default | Description |
|----------|---------|-------------|
| `os` | `rhel` | OS type for config mode |
| `os_version` | `10.0` | OS version for config mode |
| `base_packages` | *(list)* | Base OS RPMs installed in every image |
| `slurm_common_packages` | *(list)* | Shared Slurm RPMs for all roles |
| `openldap_packages` | *(list)* | Shared OpenLDAP/SSSD RPMs |
| `group_extra_packages` | *(dict)* | Per-role RPMs (keyed by role name) |

### repo_status.yml

| Variable | Default | Description |
|----------|---------|-------------|
| `repo_type` | `offline` | `offline` (Pulp) or `internet` (public CDN) |
| `pulp_port` | `2225` | Pulp server port |
| `pulp_certs_dir` | `/opt/omnia/pulp_config/pulp/settings/certs` | TLS cert directory |
| `offline_x86_repos` | *(list)* | x86_64 RPM repos with URLs |
| `offline_aarch64_url_repos` | *(list)* | aarch64 RPM repos with URLs |
| `offline_tarball_repos` | *(list)* | Tarball file repos |
| `offline_git_repos` | *(list)* | Git file repos |
| `offline_manifest_repos` | *(list)* | Manifest file repos |
| `offline_pip_repos` | *(list)* | Pip module repos |
| `generate_functional_group_packages` | `true` | Generate functional_group_packages.yml |

### CLI Overrides

```bash
python generate_dataset.py my_ds defaults --var s3_provider=powerscale
python generate_dataset.py my_ds defaults --var cluster_os_version=9.5
python generate_dataset.py my_ds defaults --var build_image_force_rebuild=true
```

Values are parsed as YAML — lists, booleans, and numbers are auto-detected.

---

## Generated Files

| Template | Output | Conditional |
|----------|--------|-------------|
| `input/image_build_config.yml.j2` | `input/image_build_config.yml` | Always |
| `input/image_build_credentials.yml.j2` | `input/image_build_credentials.yml` | Always |
| `input/package_groups.yml.j2` | `input/package_groups.yml` | Always |
| `repo_manager_output/repo_status.yml.j2` | `repo_manager_output/repo_status.yml` | Always |
| `repo_manager_output/functional_group_packages.yml.j2` | `repo_manager_output/functional_group_packages.yml` | Only when `generate_functional_group_packages: true` |

### DRY Package Definitions

Package lists are defined **once** in `defaults.yml` and reused across templates:

- **`slurm_common_packages`** — shared Slurm packages for all roles
- **`openldap_packages`** — shared OpenLDAP/SSSD packages
- **`group_extra_packages`** — per-role extra packages (keyed by role name)
- **`base_packages`** — base OS packages for all images

---

## Direct Copy from src/ (`--from-src`)

Instead of rendering templates, `--from-src` copies input files and sample
repo_manager output directly from the repo's `src/` directory:

```bash
# Offline repo_status (default)
python generate_dataset.py my_ds --from-src

# Internet repo_status
python generate_dataset.py my_ds --from-src --repo-variant internet
```

**What gets copied:**
- `src/image_build_manager/input/*.yml` → `<dataset>/input/`
- `src/image_build_manager/samples/repo_manager_output/repo_status[_internet].yml` → `<dataset>/repo_manager_output/repo_status.yml`

**Note:** `image_build_credentials.yml` and `functional_group_packages.yml` are
not present in `src/` (runtime-generated), so they won't be included.

---

## Dependencies

- **Python 3.12+**
- **Jinja2**: `pip install Jinja2`
- **PyYAML**: `pip install pyyaml`

Both are already in `requirements.txt` for the test automation framework.
