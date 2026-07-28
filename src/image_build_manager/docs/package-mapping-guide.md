# Package Mapping Guide

## Overview

The `functional_group_packages.yml` file defines which RPM packages are installed
in each OS image variant. It is the **single source of truth** for package resolution.

**Location** (runtime): `/opt/omnia/repo_manager/output/<project_name>/functional_group_packages.yml`

**Sample**: `samples/repo_manager_output/functional_group_packages.yml`

## File Structure

```yaml
# Base packages — installed in EVERY image
base_packages:
  - systemd
  - kernel
  - dracut
  - nfs-utils
  - NetworkManager
  - ...

# Functional group packages — ADDITIONAL packages per image variant
functional_groups:
  os_x86_64:
    packages: []                    # Only base packages

  slurm_node_x86_64:
    packages:
      - munge                      # Slurm common
      - slurm-slurmd               # Slurm node daemon
      - slurm-pam_slurm            # Slurm PAM module
      - openldap                   # LDAP authentication
      - sssd                       # System Security Services
      - ...

  slurm_control_node_x86_64:
    packages:
      - munge
      - slurm-slurmctld            # Slurm controller
      - slurm-slurmdbd             # Slurm database
      - mariadb-server             # Database backend
      - ...
```

## How It Works

```
image_build_config.yml                functional_group_packages.yml
┌──────────────────────────┐          ┌──────────────────────────────────┐
│ functional_groups:       │          │ base_packages: [...]             │
│   - name: slurm_node_x86│──┐       │ functional_groups:               │
│   - name: os_x86_64     │  └──────▶│   slurm_node_x86_64:            │
└──────────────────────────┘          │     packages: [munge, ...]      │
                                      └──────────────────────────────────┘
                                                  │
                                  ┌───────────────┼───────────────┐
                                  ▼                               ▼
                         base_image_packages           compute_images_dict
                         (flat RPM list)               (dict per group)
                                  │                               │
                                  ▼                               ▼
                         Base OS image              Compute image per group
                         (all base RPMs)            (base + group RPMs)
```

1. `image_build_config.yml` lists which functional groups to build
2. `functional_group_packages.yml` maps each group to its RPM packages
3. `fetch_build_packages` role loads the mapping and creates:
   - `base_image_packages` — flat list from `base_packages`
   - `compute_images_dict` — dict keyed by group name, each with `packages` list
4. `build_os_images` role builds one base image + one compute image per group

## Customization

### Adding packages to a functional group

Edit `functional_group_packages.yml`:

```yaml
functional_groups:
  slurm_node_x86_64:
    packages:
      - munge
      - slurm-slurmd
      - my-custom-package          # <-- Add your package here
```

### Adding a new functional group

1. Add the group to `functional_group_packages.yml`:

```yaml
functional_groups:
  my_custom_group_x86_64:
    packages:
      - package-a
      - package-b
```

2. Enable it in `image_build_config.yml`:

```yaml
functional_groups:
  - name: "my_custom_group_x86_64"
```

3. The group name **must** end with `_x86_64` or `_aarch64`.

### Adding base packages (all images)

```yaml
base_packages:
  - systemd
  - kernel
  - my-base-package               # <-- Added to ALL images
```

## Package Name Rules

- Package names must match RPM package names available in the Pulp repos
  defined in `repo_status.yml`
- Use the **RPM package name** (not the binary name)
- Example: `slurm-slurmd` (not `slurmd`)
- Packages are resolved by `dnf` during image build — if a package is not
  found in any configured repo, the build will fail

## Valid Functional Group Names

From `FUNCTIONAL_GROUP_LAYER_MAP` in `plugins/module_utils/build_image/config.py`:

### x86_64

| Group Name | Layer | Description |
|------------|-------|-------------|
| `os_x86_64` | compute | Base OS only |
| `slurm_node_x86_64` | compute | Slurm compute node |
| `slurm_control_node_x86_64` | management | Slurm controller |
| `login_node_x86_64` | compute | Login/access node |
| `login_compiler_node_x86_64` | compute | Login node with compilers |
| `service_kube_control_plane_first_x86_64` | management | K8s first control plane |
| `service_kube_control_plane_x86_64` | management | K8s control plane |
| `service_kube_node_x86_64` | compute | K8s worker node |

### aarch64

| Group Name | Layer | Description |
|------------|-------|-------------|
| `os_aarch64` | compute | Base OS only |
| `slurm_node_aarch64` | compute | Slurm compute node |
| `login_node_aarch64` | compute | Login/access node |
| `login_compiler_node_aarch64` | compute | Login node with compilers |

## Historical Context (Omnia Mono-Repo)

In the legacy Omnia mono-repo, package resolution used:

1. `software_config.json` — listed enabled software modules
2. `config/<arch>/<os>/<ver>/*.json` — per-software RPM lists
3. `image_package_collector.py` — Python module that read both and merged
4. `base_image_package_collector.py` — collected base/admin/debug packages

All of this is **replaced** by the single `functional_group_packages.yml` file.
