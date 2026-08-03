# Image Build Manager -- Architecture

## System Context

```
  repo_status.yml                                                    build_status.yml
  functional_group_packages.yml                                      S3 artifacts
  +---------------------+     +-------------------------------------+     +-----------+
  |                     |     |       Image Build Manager            |     |           |
  |  repo_manager       |---->|                                     |---->| orchestr- |
  |  (upstream)         |     |  setup -> validate -> prepare       |     | ator      |
  |                     |     |         -> build -> write_status    |     | (consumer)|
  +---------------------+     +-------------------------------------+     +-----------+
                                        |              |
                                   MinIO S3      OCI Registry
                                  (boot-images)  (image-builder)
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
- Validate prerequisite files exist (fail-fast):
  `image_build_config.yml`, `repo_status.yml`, `functional_group_packages.yml`
- Load `repo_status.yml` -- RPM repo URLs, OS metadata, `repo_manager.certificates.server_crt`
- Validate repo manager certificate (derived from `repo_status.yml`; skip if empty)

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
- Create S3 buckets: `boot-images`, `efi-images`

### Step 4: Build (tag: build)

Roles: `fetch_build_packages`, `build_os_images`

- Write `functional_groups_config.yml` from config
- Load `functional_group_packages.yml` -- split into `base_image_packages` + `compute_images_dict`
- Build base OS image (OpenCHAMI image-builder or image-thrillhouse)
- Build compute images per functional group with concurrency control
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
       |           +---> deploy_registry
       |
       +---> fetch_build_packages ---> build_os_images ---> write_build_status
       |
       +---> cleanup_build_artifacts
```

## Data Contract

### Inputs

| File | Source | Purpose |
|------|--------|---------|
| `image_build_config.yml` | `input/project_default/` | S3, groups, build params |
| `repo_status.yml` | repo_manager output | RPM repo URLs, OS metadata, certs |
| `functional_group_packages.yml` | repo_manager output | Group-to-RPM mapping |

### Outputs

| File | Location | Purpose |
|------|----------|---------|
| `build_status.yml` | `output/<project>/` | S3 artifact paths per functional group |

## Key Design Decisions

1. **Standalone domain** -- no dependency on other domains at code level
2. **Contract-based** -- reads `repo_status.yml`, writes `build_status.yml`
3. **No `software_config.json`** -- replaced by `functional_group_packages.yml`
4. **Bare-metal only** -- no container or Omnia core required for playbook
5. **Single mapping file** -- `functional_group_packages.yml` is the single source
   of truth for which RPMs go into each image variant
6. **Dual builder support** -- `image-builder` (standard) or `image-thrillhouse` (next-gen)
