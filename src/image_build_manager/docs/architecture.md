# Image Build Manager -- Architecture

## System Context

```
  repo_status.yml                                                    build_status.yml
  catalog_rhel.json (or package_groups.yml)                          S3 artifacts
  +---------------------+     +-------------------------------------+     +-----------+
  |                     |     |       Image Build Manager            |     |           |
  |  repo_manager       |---->|                                     |---->| orchestr- |
  |  (upstream)         |     |  setup -> validate -> prepare       |     | ator      |
  |                     |     |         -> build -> write_status    |     | (consumer)|
  +---------------------+     +-------------------------------------+     +-----------+
                                       |              |
                                  MinIO S3      OCI Registry
                                 (boot-images)  (+ regctl)
```

## Execution Mode

**Bare-metal only.** Runs directly on RHEL host via `ansible-playbook`.
All tasks execute locally (`connection: local`) except aarch64 builds
which SSH to a remote ARM node.

## Execution Flow

### Step 0: Setup (tag: always)

Role: `image_build_setup`

- Validate tags and tag combinations
- Load environment variables from `omnia.env`
- Set project directories and host vars
- Set `functional_groups_source` (`config` or `catalog`)
- Validate prerequisite files exist (fail-fast):
  - `image_build_config.yml` — always required
  - `repo_status.yml` — always required
  - `package_groups.yml` — when `functional_groups_source: "config"`
  - `CATALOG_FILE_PATH` — when `functional_groups_source: "catalog"`
- Load `repo_status.yml` via `parse_repo_status` module
- Validate repo manager certificate (if present)

### Step 1: Validate (tag: validate)

Roles: `validate_image_build_input`, `validate_build_runtime`

- L1 schema validation via `input_validation/schema/image_build_config.json`
- L2 logic validation (S3 provider, aarch64 host, async timing)
- No credentials required

### Step 2: Credentials (tag: always, skipped for validate/cleanup)

Role: `collect_build_credentials`

- Prompt for S3 access/secret keys (Ansible Vault encrypted)
- Prompt for aarch64 SSH password (if ARM host configured)

### Step 3: Prepare (tag: prepare)

Roles: `deploy_minio`, `deploy_registry`

- Deploy MinIO S3 via Podman Quadlet (if provider=minio)
- Deploy local OCI container registry via Podman Quadlet
- Install and configure `regctl` for image verification (idempotent)
- Create S3 buckets: `boot-images`, `efi-images`

### Step 4: Build (tag: build)

Roles: `fetch_build_packages`, `build_os_images`

- Dual-mode package resolution:
  - **Config mode**: load `package_groups.yml` → `base_image_packages` + `compute_images_dict`
    - Functional groups derived from `package_groups.yml` keys (no separate list needed)
    - OS type and version from `os` / `os_version` fields in `package_groups.yml`
  - **Catalog mode**: parse catalog JSON via `parse_catalog` module → same output shape
    - Layer classification by **name** (not component membership)
    - Baseos layers → `base_image_packages`; compute layers → `compute_images_dict`
    - OS type (`cluster_os_type`) extracted from baseos group's `os` field
    - OS version (`cluster_os_version`) extracted from baseos group's `os_version` field
- Build base OS image (OpenCHAMI image-builder or image-thrillhouse)
- Build compute images per functional group via `image_build_orchestrator` (concurrency control)
  - `_orchestrator_cmds` defensively initialized before build loop
- Skip compute builds when `compute_images_dict` is empty
- Verify pushed images via `regctl manifest`
- Upload artifacts to S3 (boot-images + efi-images buckets)
- Write `build_status.yml` with per-group S3 artifact paths

### Step 5: Cleanup (tag: cleanup)

Role: `cleanup_build_artifacts`

- Stop and remove MinIO + Registry containers
- Remove build artifacts, credentials, S3 data
- Remove firewall ports and systemd entries

## Role Dependency Graph

```
image_build_setup
       |
       +---> validate_image_build_input ---> validate_build_runtime
       |
       +---> collect_build_credentials
       |           |
       |           +---> deploy_minio
       |           +---> deploy_registry (+ regctl install)
       |
       +---> fetch_build_packages ---> build_os_images ---> write_build_status
       |
       +---> cleanup_build_artifacts
```

## Data Contract

### Inputs

| File | Source | Purpose |
|------|--------|---------|
| `image_build_config.yml` | `input/project_default/` | S3, build mode, build params |
| `repo_status.yml` | repo_manager output | RPM repo URLs, OS metadata |
| `package_groups.yml` | `input/project_default/` | OS metadata + group-to-RPM mapping (config mode) |
| `catalog_rhel.json` | `CATALOG_FILE_PATH` env var | Catalog JSON (catalog mode) |

### Outputs

| File | Location | Purpose |
|------|----------|---------|
| `build_status.yml` | `output/<project>/` | S3 artifact paths per functional group |

## Key Design Decisions

1. **Standalone domain** -- no dependency on other domains at code level
2. **Contract-based** -- reads `repo_status.yml`, writes `build_status.yml`
3. **Dual-mode package resolution** -- `config` (manual `package_groups.yml`) or `catalog` (catalog JSON)
4. **Bare-metal only** -- no container or Omnia core required for playbook
5. **Layer-name classification** -- baseos vs compute determined by layer name prefix, not component membership
6. **Dual builder support** -- `image-builder` (standard) or `image-thrillhouse` (next-gen)
7. **Guaranteed regctl** -- installed by `deploy_registry`, used unconditionally for verification
