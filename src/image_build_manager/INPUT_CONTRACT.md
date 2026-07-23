# image_build_manager — Input Contract

> **Last Updated**: Jul 21, 2026 | **Domain**: `image_build_manager`

This document defines all input files consumed by the `image_build_manager` domain.

---

## 1. image_build_config.yml

**Purpose**: Per-domain input configuration for image_build_manager.

**Location**: `input/project_default/image_build_manager/image_build_config.yml`

**Owner**: User (manually configured)

**Schema**: `src/common/.../schema/image_build_config.json`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `s3_configurations.provider` | string | Yes | `"minio"` | S3 backend: `minio` (deployed locally) or `powerscale` (external) |
| `s3_configurations.endpoint_url` | string | No | `""` | S3 endpoint URL; auto-detected for MinIO, required for PowerScale |
| `repo_manager_output_path` | string | No | `""` | Path to `repo_status.yml`; empty = default location |
| `aarch64_inventory_host_ip` | string | No | `""` | ARM build host IP; empty = skip aarch64 builds |
| `aarch64_ssh_user` | string | No | `"root"` | SSH user for ARM build host |
| `build_image.job_async` | int | No | `7200` | Max async wait for image build (seconds) |
| `build_image.job_retry` | int | No | `240` | Max retries for async status check |
| `build_image.job_delay` | int | No | `30` | Delay between async status checks (seconds) |

**Validation**: `validate_build_config` role validates existence, YAML syntax, and required fields.

---

## 2. image_build_credentials.yml

**Purpose**: Vault-encrypted credentials for S3 and provisioning.

**Location**: `input/project_default/image_build_credentials.yml`

**Owner**: `credential_utility` (auto-generated on first run via interactive prompts)

**Vault Key**: `input/project_default/.image_build_credentials_key`

**Schema**: `src/common/.../schema/image_build_credentials.json`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `s3_access_id` | string | Yes (MinIO) | S3 access key ID; defaults to `admin` for MinIO |
| `s3_secret_key` | string | Yes (MinIO) | S3 secret key |
| `provision_password` | string | Yes | Root password for provisioned nodes |

**Notes**:
- Created by `credential_utility` with tag `image_build_manager`
- For PowerScale provider, S3 credentials point to the external endpoint

---

## 3. repo_status.yml (upstream dependency)

**Purpose**: Output from `repo_manager` domain consumed as input by `image_build_manager`.

**Location**: `output/project_default/repo_manager/repo_status.yml`  
(or custom path via `repo_manager_output_path` in `image_build_config.yml`)

**Producer**: `repo_manager` domain

**Consumer**: `image_build_manager.yml` (Step 4 — Pre-check)

### Structure

```yaml
overall_status: "success"

tarball_base_url: "https://<admin_nic_ip>:2225/pulp/content/.../tarballs/"
manifest_base_url: "https://<admin_nic_ip>:2225/pulp/content/.../manifests/"
pip_base_url: "https://<admin_nic_ip>:2225/pulp/content/.../pip/"
git_base_url: "https://<admin_nic_ip>:2225/pulp/content/.../git/"

repo_manager:
  port: 2225
  certificates:
    server_crt: "/opt/omnia/pulp/settings/certs/pulp_webserver.crt"
    server_key: "/opt/omnia/pulp/settings/certs/pulp_webserver.key"
    certs_dir: "/opt/omnia/pulp/settings/certs"

rpm_repos:
  x86_64:
    baseos: "https://<admin_nic_ip>:2225/pulp/content/.../x86_64_rhel_10.0_baseos/"
    appstream: "https://<admin_nic_ip>:2225/pulp/content/.../x86_64_rhel_10.0_appstream/"
    # ... (codeready_builder, epel, doca, omnia-additional, cuda, etc.)
  aarch64:
    baseos: "https://<admin_nic_ip>:2225/pulp/content/.../aarch64_rhel_10.0_baseos/"
    appstream: "https://<admin_nic_ip>:2225/pulp/content/.../aarch64_rhel_10.0_appstream/"
    # ... (codeready_builder, epel, doca)

user_repos:
  x86_64:
    slurm_custom: "https://<admin_nic_ip>:2225/pulp/content/.../x86_64_rhel_10.0_slurm_custom/"
  aarch64:
    slurm_custom: "https://<admin_nic_ip>:2225/pulp/content/.../aarch64_rhel_10.0_slurm_custom/"
```

### Validation Rules

| Rule | Error Behavior |
|------|---------------|
| File must exist | Fail with "repo_status.yml not found" |
| `overall_status` must be `"success"` | Fail with "repo_manager did not complete successfully" |
| `repo_manager` section must exist | Fail with "missing repo_manager section" |
| `repo_manager.certificates.server_crt` must exist | Fail with "missing certificate path" |
| `repo_manager.port` must exist | Fail with "missing Pulp port" |
| `rpm_repos` must contain valid URLs for target arch | Fail with "missing RPM repos" |

### Facts Set from repo_status.yml

| Fact | Source | Description |
|------|--------|-------------|
| `pulp_webserver_cert_path` | `repo_manager.certificates.server_crt` | Localhost cert path |
| `pulp_port` | `repo_manager.port` | Pulp HTTPS port |
| `pulp_cert_oim_path` | Translated from `server_crt` | OIM-mount cert path (`/opt/omnia` → `oim_shared_path`) |
| `repo_manager_repos_x86_64` | `rpm_repos.x86_64` + `user_repos.x86_64` | List of `{name, base_url, gpg}` |
| `repo_manager_repos_aarch64` | `rpm_repos.aarch64` + `user_repos.aarch64` | List of `{name, base_url, gpg}` |

---

## 4. software_config.json (shared input)

**Purpose**: Cluster OS type, version, and software stack definition.

**Location**: `input/project_default/software_config.json`

**Owner**: User (shared across domains)

**Consumed Fields**:

| Field | Usage in image_build_manager |
|-------|------------------------------|
| `cluster_os_type` | Selects base image type (e.g., `rhel`) |
| `cluster_os_version` | Sets OS version for image naming (e.g., `10.0`) |
| `softwares[].name` | Determines functional groups and packages |

---

## 5. Dependency Summary

```
                    ┌─────────────────────────┐
                    │   credential_utility     │
                    │  (tag: image_build_mgr)  │
                    └────────┬────────────────┘
                             │ produces
                             ▼
                    ┌─────────────────────────┐
                    │ image_build_credentials  │
                    │        .yml              │
                    └────────┬────────────────┘
                             │
  ┌──────────────┐           │           ┌──────────────────┐
  │ image_build  │           │           │  repo_status.yml │
  │  _config.yml │───────────┼──────────▶│  (from repo_mgr) │
  └──────────────┘           │           └──────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │  image_build_manager.yml │
                    └─────────────────────────┘
```
