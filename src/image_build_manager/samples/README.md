# image_build_manager Sample Files

This directory contains sample configuration files that document the input and output contracts for the image_build_manager domain.

## Files

### repo_status.yml

**Purpose**: Input contract produced by the `repo_manager` domain and consumed by `image_build_manager`.

**Location**: `/opt/omnia/output/repo_manager/repo_status.yml`

**Producer**: `repo_manager.yml` (repo_manager domain)

**Consumer**: `image_build_manager.yml` (Step 4 - Pre-check)

**Structure**:
```yaml
overall_status: "success"  # or "failed"

# Base URLs for other content types
tarball_base_url: "http://{{ admin_nic_ip }}:2225/pulp/content/tarballs/"
manifest_base_url: "http://{{ admin_nic_ip }}:2225/pulp/content/manifests/"
pip_base_url: "http://{{ admin_nic_ip }}:2225/pulp/content/pip/"
git_base_url: "http://{{ admin_nic_ip }}:2225/pulp/content/git/"

repo_manager:
  port: 2225
  certificates:
    server_crt: "/opt/omnia/pulp/settings/certs/pulp_webserver.crt"
    server_key: "/opt/omnia/pulp/settings/certs/pulp_webserver.key"
    certs_dir: "/opt/omnia/pulp/settings/certs"

# RPM Repository Base URLs
rpm_repos:
  x86_64:
    baseos: "http://{{ admin_nic_ip }}:2225/pulp/content/rhel/baseos/x86_64/"
    appstream: "http://{{ admin_nic_ip }}:2225/pulp/content/rhel/appstream/x86_64/"
    codeready_builder: "http://{{ admin_nic_ip }}:2225/pulp/content/rhel/codeready-builder/x86_64/"
    epel: "http://{{ admin_nic_ip }}:2225/pulp/content/epel/x86_64/"
    slurm_custom: "http://{{ admin_nic_ip }}:2225/pulp/content/slurm_custom/x86_64/"
    doca: "http://{{ admin_nic_ip }}:2225/pulp/content/doca/x86_64/"
  aarch64:
    baseos: "http://{{ admin_nic_ip }}:2225/pulp/content/rhel/baseos/aarch64/"
    appstream: "http://{{ admin_nic_ip }}:2225/pulp/content/rhel/appstream/aarch64/"
    codeready_builder: "http://{{ admin_nic_ip }}:2225/pulp/content/rhel/codeready-builder/aarch64/"
    epel: "http://{{ admin_nic_ip }}:2225/pulp/content/epel/aarch64/"
    slurm_custom: "http://{{ admin_nic_ip }}:2225/pulp/content/slurm_custom/aarch64/"
    doca: "http://{{ admin_nic_ip }}:2225/pulp/content/doca/aarch64/"

# User-Defined Repositories (from local_repo_config.yml)
user_repos:
  x86_64:
    custom_repo_1: "http://{{ admin_nic_ip }}:2225/pulp/content/custom_repo_1/x86_64/"
    custom_repo_2: "http://{{ admin_nic_ip }}:2225/pulp/content/custom_repo_2/x86_64/"
  aarch64:
    custom_repo_1: "http://{{ admin_nic_ip }}:2225/pulp/content/custom_repo_1/aarch64/"
    custom_repo_2: "http://{{ admin_nic_ip }}:2225/pulp/content/custom_repo_2/aarch64/"
```

**Validation**:
- `overall_status` must be `"success"`
- `repo_manager` section must exist with `certificates.server_crt` and `port`
- `rpm_repos` must contain valid URLs for target architectures

**Notes**:
- The `{{ admin_nic_ip }}` template variable is resolved by repo_manager at runtime
- `rpm_repos.aarch64` is used by `prepare_arm_node` to dynamically generate `pulp.repo` on ARM build hosts
- `aarch64_repo_store_path` was removed in Omnia 2.2 — AArch64 repo is now generated dynamically

---

### build_status.yml

**Purpose**: Output contract produced by `image_build_manager` and consumed by the `provision` domain for BSS template rendering.

**Location**: 
- Latest: `/opt/omnia/output/project_default/build_status.yml`
- Versioned: `/opt/omnia/output/project_default/image_build_manager/build_status_<version>_<timestamp>.yml`

**Producer**: `image_build_manager.yml` (Step 8 - Write build_status)

**Consumer**: 
- `provision/roles/provision_validations/tasks/validate_image.yml`
- `provision/roles/configure_ochami/tasks/configure_bss_group.yml`

**Structure**:
```yaml
overall_status: "success"  # or "failed"

s3_configurations:
  endpoint_url: "http://10.20.0.1:9000"  # or http://<admin_nic_ip>:9000 for MinIO
  bucket: "boot-images"

functional_group_images:
  - x86_64:
    - functional_group: "slurm_control_node_x86_64"
      kernel: "boot-images/efi-images/slurm_control_node_x86_64/rhel-slurm_control_node_x86_64_omnia_2.2.0.0/vmlinuz"
      initrd: "boot-images/efi-images/slurm_control_node_x86_64/rhel-slurm_control_node_x86_64_omnia_2.2.0.0/initramfs.img"
      image: "boot-images/slurm_control_node_x86_64/rhel-slurm_control_node_x86_64_omnia_2.2.0.0"
  - aarch64:
    - functional_group: "slurm_node_aarch64"
      kernel: "boot-images/efi-images/slurm_node_aarch64/rhel-slurm_node_aarch64_omnia_2.2.0.0/vmlinuz"
      initrd: "boot-images/efi-images/slurm_node_aarch64/rhel-slurm_node_aarch64_omnia_2.2.0.0/initramfs.img"
      image: "boot-images/slurm_node_aarch64/rhel-slurm_node_aarch64_omnia_2.2.0.0"
```

**Key Changes in Omnia 2.2**:
- `overall_status` changed from `"completed"` to `"success"`
- `s3_endpoint_url` replaced with `s3_configurations` block containing `endpoint_url` and `bucket`
- `functional_group_images` is now grouped by architecture (x86_64, aarch64) instead of a flat list
- Image entries now include `kernel`, `initrd`, and `image` paths instead of `s3_prefix`
- `build_arch_list` removed — architecture grouping is implicit in `functional_group_images`

**S3 Endpoint Behavior**:
- **MinIO**: Auto-detected as `http://<admin_nic_ip>:9000` when `endpoint_url` is empty
- **PowerScale**: Uses configured `endpoint_url` as-is

**Notes**:
- Functional group names (e.g., `slurm_control_node_x86_64`) already include architecture suffix
- Kernel/initrd paths use `efi-images/` subdirectory for UEFI boot
- Image path is the full S3 key for the rootfs image
