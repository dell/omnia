# Dataset Generator

Custom dataset generator for the image\_build\_manager test automation.

By default, the test framework uses input files **directly from
`src/image_build_manager/`** — no dataset generation is needed for
standard testing. This tool is only required when you need a
**custom dataset** with non-default values (e.g., different repo
type, S3 provider, or build settings).

---

## Default Behaviour (No Dataset Needed)

When `dataset: ""` in `test_config.yml` (the default), the framework
reads files directly from the source tree:

| File | Source Path |
|------|-------------|
| `image_build_config.yml` | `src/image_build_manager/input/` |
| `package_groups.yml` | `src/image_build_manager/input/` |
| `repo_status.yml` | `src/image_build_manager/samples/repo_manager_output/` |

This is the **recommended mode** — input files always stay in sync
with the source code. No dataset folder is created or maintained.

---

## When to Use a Custom Dataset

Use the generator when you need to:

- Test with **different repo types** (offline vs internet)
- Override **S3 provider** (minio vs powerscale)
- Change **build settings** (timeout, force rebuild, etc.)
- Create a **reproducible snapshot** of input files for CI

---

## Quick Start

```bash
cd test/image_build_manager/datasets/generator/

# Generate a custom dataset from templates
python generate_dataset.py my_offline_ds defaults
python generate_dataset.py my_internet_ds internet
python generate_dataset.py my_custom defaults --var s3_provider=powerscale

# Copy files directly from src/ into a dataset folder
python generate_dataset.py my_src_ds --from-src
python generate_dataset.py my_src_ds --from-src --repo-variant internet

# List available profiles
python generate_dataset.py --list-profiles
```

Then set `dataset: "my_offline_ds"` in `test_config.yml` to use it.

---

## Architecture

```
generator/
├── generate_dataset.py          # CLI tool
├── README.md                    # This file
├── profiles/                    # Variable profiles (YAML)
│   ├── defaults.yml             # Base profile — all shared values
│   └── internet.yml             # Override: public repo URLs
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

1. **`defaults.yml`** — all shared values (packages, build settings,
   offline repo definitions). This is the base profile.
2. **Profile overrides** (e.g., `internet.yml`) — override only what differs.
3. **CLI `--var` flags** — override individual values at generation time.
4. **Jinja2 templates** — render into concrete YAML files.

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
# Edit — only override keys that differ from defaults.yml
```

---

## Key Parameters

### image\_build\_config.yml

| Variable | Default | Description |
|----------|---------|-------------|
| `s3_provider` | `minio` | S3 backend: `minio` or `powerscale` |
| `image_build_type` | `image-builder` | Builder type |
| `build_image_max_parallel` | `0` | Max concurrent builds (0 = unlimited) |
| `build_image_build_timeout` | `7200` | Build timeout in seconds |
| `build_image_force_rebuild` | `false` | Bypass package hash cache |
| `functional_groups_source` | `catalog` | Group source: `config` or `catalog` |
| `aarch64_inventory_host_ip` | `""` | ARM build host IP (empty = skip) |

### repo\_status.yml

| Variable | Default | Description |
|----------|---------|-------------|
| `repo_type` | `offline` | `offline` (Pulp) or `internet` (public CDN) |
| `pulp_port` | `2225` | Pulp server port |
| `admin_nic_ip` | `""` | Admin network IP (template placeholder) |

### CLI Overrides

```bash
python generate_dataset.py my_ds defaults --var s3_provider=powerscale
python generate_dataset.py my_ds defaults --var build_image_force_rebuild=true
```

Values are parsed as YAML — booleans, numbers, and lists are auto-detected.

---

## Direct Copy from src/ (`--from-src`)

Instead of rendering templates, `--from-src` copies files directly from
the repo's `src/` directory into a dataset folder:

```bash
python generate_dataset.py my_ds --from-src
python generate_dataset.py my_ds --from-src --repo-variant internet
```

**What gets copied:**

- `src/image_build_manager/input/*.yml` → `<dataset>/input/`
- `src/.../samples/repo_manager_output/repo_status.yml` → `<dataset>/repo_manager_output/`
- A placeholder `image_build_credentials.yml` is auto-created

---

## Generated Output

| Template | Output | Conditional |
|----------|--------|-------------|
| `input/image_build_config.yml.j2` | `input/image_build_config.yml` | Always |
| `input/image_build_credentials.yml.j2` | `input/image_build_credentials.yml` | Always |
| `input/package_groups.yml.j2` | `input/package_groups.yml` | Always |
| `repo_manager_output/repo_status.yml.j2` | `repo_manager_output/repo_status.yml` | Always |
| `repo_manager_output/functional_group_packages.yml.j2` | `repo_manager_output/functional_group_packages.yml` | When `generate_functional_group_packages: true` |

---

## Coding Standards

All Python code in this directory follows these CI requirements:

- **Pylint**: Score 10.00/10 (no `# pylint: disable` allowed)
- **Bandit**: Zero findings (security scan)
- **Gitleaks**: No hardcoded IPs, passwords, or secrets
- **DCO**: All commits must be signed off (`git commit -s`)

---

## Dependencies

- **Python 3.12+**
- **Jinja2**: `pip install Jinja2`
- **PyYAML**: `pip install pyyaml`

Both are already in `test/image_build_manager/requirements.txt`.
