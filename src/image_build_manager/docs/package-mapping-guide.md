# Package Mapping Guide

## Overview

`functional_group_packages.yml` defines which RPM packages are installed in each
OS image variant. It is the **single source of truth** for package resolution.

**Location**: Path from `repo_manager.package_list` in `repo_status.yml`

**Sample**: `samples/repo_manager_output/functional_group_packages.yml`

---

## Structure

```yaml
base_packages:
  - systemd
  - kernel
  - dracut
  - nfs-utils
  - NetworkManager

functional_groups:
  os_x86_64:
    packages: []

  slurm_node_x86_64:
    packages:
      - munge
      - slurm-slurmd
      - slurm-pam_slurm
      - openldap
      - sssd

  slurm_control_node_x86_64:
    packages:
      - munge
      - slurm-slurmctld
      - slurm-slurmdbd
      - mariadb-server
```

---

## How It Works

1. `image_build_config.yml` lists which functional groups to build
2. `functional_group_packages.yml` maps each group to RPM packages
3. `fetch_build_packages` role creates:
   - `base_image_packages` -- flat list from `base_packages`
   - `compute_images_dict` -- dict per group with `packages` list
4. `build_os_images` role builds one base image + one compute image per group

```
config: functional_groups[]     packages: base_packages + functional_groups
+-------------------------+     +----------------------------------+
| - slurm_node_x86_64    | --> | base_image_packages (all images) |
| - os_x86_64            |     | compute_images_dict (per group)  |
+-------------------------+     +----------------------------------+
                                            |
                                  OpenCHAMI image-builder --> S3
```

---

## Customization

### Add packages to a group

```yaml
functional_groups:
  slurm_node_x86_64:
    packages:
      - munge
      - slurm-slurmd
      - my-custom-package      # add here
```

### Add a new functional group

1. Add to `functional_group_packages.yml`:
```yaml
functional_groups:
  my_custom_group_x86_64:
    packages:
      - package-a
      - package-b
```

2. Enable in `image_build_config.yml`:
```yaml
functional_groups:
  - name: "my_custom_group_x86_64"
```

Group name **must** end with `_x86_64` or `_aarch64`.

### Add base packages (all images)

```yaml
base_packages:
  - systemd
  - kernel
  - my-base-package            # added to ALL images
```

---

## Package Name Rules

- Use RPM package names (not binary names): `slurm-slurmd` not `slurmd`
- Names must exist in Pulp repos defined in `repo_status.yml`
- Resolved by `dnf` during build -- missing packages fail the build

---

## Valid Functional Groups

From `FUNCTIONAL_GROUP_LAYER_MAP` in `plugins/module_utils/build_image/config.py`:

| x86_64 | Layer | aarch64 | Layer |
|--------|-------|---------|-------|
| `os_x86_64` | compute | `os_aarch64` | compute |
| `slurm_node_x86_64` | compute | `slurm_node_aarch64` | compute |
| `slurm_control_node_x86_64` | management | `login_node_aarch64` | management |
| `login_node_x86_64` | management | `login_compiler_node_aarch64` | management |
| `login_compiler_node_x86_64` | management | | |
| `service_kube_control_plane_first_x86_64` | management | | |
| `service_kube_control_plane_x86_64` | management | | |
| `service_kube_node_x86_64` | management | | |
