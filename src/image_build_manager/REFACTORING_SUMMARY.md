# Image Build Manager — Refactoring Summary

## Overview

This document tracks all refactoring changes applied to the **image_build_manager** domain
(formerly `build_manager`). The domain is responsible for building OS boot images (kernel,
initramfs, rootfs) for x86_64 and aarch64 architectures, managing S3 storage (MinIO),
container registry deployment, and producing `build_status.yml` consumed by the provision domain.

---

## 1. Domain Rename: build_manager → image_build_manager

| Item | Before | After |
|------|--------|-------|
| Directory | `src/build_manager/` | `src/image_build_manager/` |
| Main playbook | `build_manager.yml` | `image_build_manager.yml` |
| Input config | `build_manager_config.yml` | `image_build_config.yml` |
| Credential file | `build_manager_credentials.yml` | `image_build_credentials.yml` |
| Credential template | `build_manager_credential.j2` | `image_build_credential.j2` |
| Credential key | `.build_manager_credentials_key` | `.image_build_credentials_key` |
| Input subdir | `input/project_default/build_manager/` | `input/project_default/image_build_manager/` |
| Output subdir | `output/project_default/build_manager/` | `output/project_default/image_build_manager/` |
| Log path | `build_manager.log` | `image_build_manager.log` |
| Validation tag | `build_manager` | `image_build_manager` |

### Sub-playbook Rename

| Before | After |
|--------|-------|
| `prepare_build_manager.yml` | `prepare_image_build_manager.yml` |
| `rollback_build_manager.yml` | `rollback_image_build_manager.yml` |
| `upgrade_build_manager.yml` | `upgrade_image_build_manager.yml` |

### Files Updated for Rename

- All playbooks under `src/image_build_manager/playbooks/`
- All role vars and tasks under `src/image_build_manager/roles/`
- `src/image_build_manager/ansible.cfg` and `playbooks/ansible.cfg`
- `src/image_build_manager/vars/image_vars.yml`
- `src/image_build_manager/input/image_build_config.yml`
- `src/image_build_manager/samples/repo_status.yml` and `build_status.yml`
- `src/playbooks/utils/credential_utility/roles/*/vars/main.yml`
- `src/playbooks/utils/roles/common/vars/main.yml` and `tasks/main.yml`
- `src/playbooks/utils/roles/common/tasks/include_image_build_credentials.yml`
- `src/playbooks/input_validation/validate_config.yml`
- `src/common/library/module_utils/input_validation/common_utils/config.py`
- `src/main/omnia.sh`
- `src/main/containers/build_images.sh`
- `src/playbooks/prepare_oim/roles/deploy_containers/openchami/tasks/configs/main.yml`

---

## 2. Credential Ownership Transfer

| Credential | Before (prepare_oim) | After (image_build_manager) |
|------------|---------------------|-----------------------------|
| `s3_secret_key` | `omnia_config_credentials.yml` | `image_build_credentials.yml` only |
| `s3_access_id` | `omnia_config_credentials.yml` | `image_build_credentials.yml` only |
| `provision_password` | `omnia_config_credentials.yml` | `image_build_credentials.yml` (mandatory) |
| `pulp_password` | `omnia_config_credentials.yml` | Stays in `omnia_config_credentials.yml` |

---

## 3. Pulp Details Read from repo_status.yml

**All hardcoded Pulp paths removed from image_build_manager flow.**

Pulp certificate paths, repo file paths, and registry details are now read from
`repo_status.yml` (produced by repo_manager) in **Step 3** of `image_build_manager.yml`.

### repo_status.yml Contract (new fields)

```yaml
repo_manager:
  port: 2225
  certificates:
    server_crt: "/opt/omnia/pulp/settings/certs/pulp_webserver.crt"
    server_key: "/opt/omnia/pulp/settings/certs/pulp_webserver.key"
    certs_dir: "/opt/omnia/pulp/settings/certs"
```

### Facts Set from repo_status.yml (Step 4)

| Fact | Source |
|------|--------|
| `pulp_webserver_cert_path` | `repo_manager.certificates.server_crt` |
| `pulp_port` | `repo_manager.port` |

### Validation

Step 4 validates that `repo_manager` section exists in repo_status.yml with
required fields before proceeding.

### Role Vars Updated

- `roles/image_creation/vars/main.yml` — `pulp_cert_host_path`, `pulp_webserver_cert_path`,
  and container mounts now reference `hostvars['localhost']` facts
- `roles/prepare_arm_node/vars/main.yml` — `pulp_repo_store_path`, 
  `pulp_webserver_cert_path`, `ochami_aarch_64_dir` now reference facts
- `roles/image_creation/tasks/prepare_pulp_image.yml` — registry port from facts
- `roles/prepare_arm_node/tasks/main.yml` — registry port from facts

---

## 4. Container Build Scripts

### New: `src/image_build_manager/containers/build_images.sh`
Self-contained container build script for image-builder (no dependency on `_common.sh`).
`image_builder/build.sh` removed — all logic consolidated into `build_images.sh`.

### Moved: `src/containers/` → `src/main/containers/`
Core container build scripts (`build_images.sh`, `_common.sh`, Dockerfiles) moved to
`src/main/containers/`. Image-builder removed from central build dispatch.

### Removed: `src/image_build_manager/containers/image_builder/build.sh`
Redundant — all logic consolidated into `build_images.sh`. Single file is clearer.

---

## 5. Input Validation & Schema

### JSON Schemas Added
- `src/common/.../schema/image_build_config.json` — validates `image_build_config.yml`
- `src/common/.../schema/image_build_credentials.json` — validates `image_build_credentials.yml`

### config.py Updates
- `files` dict: added `image_build_config` entry
- `input_file_inventory`: `image_build_manager` tag validates `image_build_config.yml` + `software_config.json`
- `get_vault_password()`: maps `image_build_credentials.yml` → `.image_build_credentials_key`

---

## 6. MinIO/Registry Deployment

Moved from `prepare_oim` to `image_build_manager`:
- `roles/deploy_minio/` — MinIO container, S3 buckets, ACL policies
- `roles/deploy_registry/` — Local container registry

Deployed by `prepare_image_build_manager.yml` (Step 5 of `image_build_manager.yml`).

---

## 7. End-to-End Flow

```
┌──────────────────────────────────────────────────────────┐
│                     omnia.sh                             │
│  1. Creates output directory                             │
│  2. Copies image_build_manager input files               │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│              credential_utility                          │
│  Tag: image_build_manager                                │
│  Prompts: s3_secret_key, s3_access_id*, provision_pass   │
│  Writes: image_build_credentials.yml (vault-encrypted)   │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│              include_input_dir                           │
│  Sets: input_project_dir, output_project_dir             │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│          image_build_manager.yml                         │
│  Step 0: Upgrade check                                   │
│  Step 1: Credential collection (image_build_manager tag) │
│  Step 2: Resolve input/output dirs                       │
│  Step 3: Load repo_status.yml → pulp + registry facts    │
│  Step 4: Load image_build_config.yml (or legacy fallback)│
│  Step 5: Deploy MinIO + Registry (prepare)               │
│  Step 6: Build x86_64 images                             │
│  Step 7: Build aarch64 images                            │
│  Step 8: Write build_status.yml                          │
└──────────────────────────────────────────────────────────┘
```

### File Locations

```
input/project_default/
├── image_build_credentials.yml        ← s3_access_id, s3_secret_key, provision_password
├── .image_build_credentials_key
├── image_build_manager/               ← domain input configs
│   └── image_build_config.yml
└── ...other input files...

output/project_default/
├── repo_manager/
│   └── repo_status.yml                ← consumed by Step 3 (pulp + registry + repos)
├── build_status.yml                   ← latest (consumed by provision)
└── image_build_manager/
    └── build_status_<version>_<date>.yml  ← versioned copy
```

---

## 8. Upgrade & Rollback Compatibility

- **Upgrade**: S3 creds in old `omnia_config_credentials.yml` are automatically migrated
  to `image_build_credentials.yml`.
- **Rollback**: Falls back to reading S3 from old credential file if
  `image_build_credentials.yml` doesn't exist yet.
- **prepare_oim** no longer prompts for S3 creds.

---

## 9. Backward Compatibility

- No breaking changes for users who don't use image_build_manager.
- `image_build_config.yml` is **required** — no legacy fallback to `storage_config.yml`.
- `s3_configurations.endpoint_url` added for explicit S3 endpoint configuration.
- image-builder container build is now self-contained in `src/image_build_manager/containers/`
  and removed from central `src/main/containers/build_images.sh`.
- Sub-playbooks (`build_image_x86_64.yml`, `build_image_aarch64.yml`) work independently
  with proper credential utility integration and image_build_config loading.
