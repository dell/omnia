# Package Mapping Guide

## Overview

In config mode, `package_groups.yml` is the source of OS metadata, base RPMs,
and functional-group RPMs.

- Source template: `src/image_build_manager/input/package_groups.yml`
- Runtime file: `<OMNIA_DATA_PATH>/image_build_manager/input/<project>/package_groups.yml`
- Enabled by: `functional_groups_source: "config"` in `image_build_config.yml`

Catalog mode does not use this mapping. It resolves packages from the JSON file
named by `CATALOG_FILE_PATH`.

## Structure

```yaml
os: "rhel"
os_version: "10.0"

base_packages:
  - systemd
  - kernel
  - dracut
  - nfs-utils
  - NetworkManager

functional_groups:
  slurm_node_x86_64:
    packages:
      - munge
      - slurm-slurmd
      - slurm-pam_slurm

  slurm_control_node_x86_64:
    packages:
      - munge
      - slurm-slurmctld
      - slurm-slurmdbd
      - mariadb-server
```

The schema requires `os`, `os_version`, a non-empty unique `base_packages`
list, and at least one functional-group entry. Every group name must end in
`_x86_64` or `_aarch64`, and every group must contain a unique `packages` list.

## Resolution Behavior

1. `fetch_build_packages` loads the runtime `package_groups.yml`.
2. `base_packages` becomes `base_image_packages` for the architecture's base
   image.
3. Functional groups are selected directly from mapping keys that match the
   current architecture. There is no separate group allow-list in
   `image_build_config.yml`.
4. Architecture-matching entries with an empty `packages` list are skipped.
5. Any entry whose name contains `driver_group` is skipped because driver
   packages are intended for post-boot installation.
6. Each remaining entry becomes one item in `compute_images_dict` and one
   compute-image build.

```text
package_groups.yml
  base_packages ------------------------> base OS image
  functional_groups.*_<architecture>
       | non-empty and not driver_group
       +--------------------------------> one compute image per group
```

## Customization

### Add packages to a group

Edit the staged runtime file so setup does not overwrite the customization:

```yaml
functional_groups:
  slurm_node_x86_64:
    packages:
      - munge
      - slurm-slurmd
      - my-custom-package
```

### Add a functional group

Add the entry to `package_groups.yml`; no change to
`image_build_config.yml` is needed:

```yaml
functional_groups:
  my_custom_group_x86_64:
    packages:
      - package-a
      - package-b
```

Use the target architecture suffix and provide at least one package if the
group should produce an image.

### Add packages to every image

```yaml
base_packages:
  - systemd
  - kernel
  - my-base-package
```

## Package Rules

- Use RPM package names, not installed binary names: for example,
  `slurm-slurmd`, not `slurmd`.
- Packages must be available from a repository in the validated
  `repo_status.yml`.
- A missing RPM causes the OpenCHAMI build to fail during package resolution.
- Lists must not contain duplicates.

## Shipped Functional Groups

The source template currently defines:

| x86_64 | aarch64 |
|--------|---------|
| `os_x86_64` (empty; skipped) | `os_aarch64` (empty; skipped) |
| `slurm_node_x86_64` | `slurm_node_aarch64` |
| `slurm_control_node_x86_64` | `login_node_aarch64` |
| `login_node_x86_64` | `login_compiler_node_aarch64` |
| `login_compiler_node_x86_64` | |
| `service_kube_control_plane_first_x86_64` (empty; skipped) | |
| `service_kube_control_plane_x86_64` (empty; skipped) | |
| `service_kube_node_x86_64` (empty; skipped) | |

These are defaults, not a hard-coded allow-list. Any schema-valid group name
with a non-empty package list is eligible for its matching architecture.
