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

---

## Tag Reference

All tags are **mutually exclusive** — run exactly ONE tag (or none for default flow).

```bash
cd src/image_build_manager/playbooks
ansible-playbook image_build_manager.yml                        # Default: prepare + build
ansible-playbook image_build_manager.yml --tags precheck        # Env + connectivity precheck
ansible-playbook image_build_manager.yml --tags validate        # Validate config only
ansible-playbook image_build_manager.yml --tags credentials     # Collect/update credentials only
ansible-playbook image_build_manager.yml --tags prepare         # Deploy MinIO + Registry
ansible-playbook image_build_manager.yml --tags build           # Build images only
ansible-playbook image_build_manager.yml --tags execute         # Build images (alias for build)
ansible-playbook image_build_manager.yml --tags cleanup         # Remove all infrastructure
ansible-playbook image_build_manager.yml --tags cleanup_images  # Delete built images only
ansible-playbook image_build_manager.yml --tags upgrade         # Upgrade (placeholder)
ansible-playbook image_build_manager.yml --tags rollback        # Rollback (placeholder)
```

### Tag Behavior Matrix

| Tag | Setup | Validate | Credentials | Action | repo_status needed |
|-----|-------|----------|-------------|--------|-------------------|
| *(none)* | Yes | Yes | Yes | prepare + build + write_status | Yes |
| `precheck` | Yes | **No** | **No** | precheck_environment | No |
| `validate` | Yes | Yes | **No** | *(validate only)* | No |
| `credentials` | Yes | Yes | Yes | *(credentials only)* | No |
| `prepare` | Yes | Yes | Yes | deploy_minio + deploy_registry | No |
| `build` / `execute` | Yes | Yes | Yes | build x86_64/aarch64 + write_status | Yes |
| `cleanup` | Yes | **No** | **No** | cleanup_image_build_manager | No |
| `cleanup_images` | Yes | **No** | **No** | cleanup_images | No |
| `upgrade` | Yes | Yes | Yes | placeholder | No |
| `rollback` | Yes | Yes | Yes | placeholder | No |

### Invalid Tag Combinations

Tags like `prepare + cleanup`, `build + cleanup`, `precheck + build`, etc. are rejected
at startup with a clear error message. See `image_build_setup/vars/main.yml` for the
complete list.

---

## Execution Flow

### Step 0: Setup (tag: always)

Role: `image_build_setup`

- Validate provided tags against `supported_tags` and `invalid_tag_combinations`
- Set `skip_build_credentials` flag for tags that don't need credentials
- Determine `needs_repo_status` (only for build/execute/default flow)
- Load environment variables from `omnia.env`
- Set project directories and host vars
- Set `functional_groups_source` (`config` or `catalog`)
- Validate prerequisite files exist (fail-fast, skipped for cleanup/precheck):
  - `image_build_config.yml` — always required
  - `repo_status.yml` — required for build-related tags
  - `package_groups.yml` — when `functional_groups_source: "config"`
  - `CATALOG_FILE_PATH` — when `functional_groups_source: "catalog"`
- Load `repo_status.yml` via `parse_repo_status` module (when needed)
- Validate repo manager certificate (if present)

### Step 1: Validate (tag: always, skipped for precheck)

Roles: `validate_image_build_input`

- L1 schema validation via `input_validation/schema/image_build_config.json`
- L2 logic validation (S3 provider, aarch64 host, build timeout)
- L2 catalog validation (when `functional_groups_source: "catalog"` and `CATALOG_FILE_PATH` set):
  - Schema structure checks (functionallayer, groups, packages)
  - Structure validation: layers have name/components, groups is dict
- No credentials required

### Step 2: Credentials (tag: always, skipped for validate/cleanup/cleanup_images/precheck)

Role: `collect_build_credentials`

- Prompt for S3 access/secret keys (Ansible Vault encrypted)
- Prompt for aarch64 SSH password (if ARM host configured)
- Output: `input/<project>/image_build_credentials.yml` (vault-encrypted)

### Step 3: Precheck (tag: precheck, opt-in only)

Role: `precheck_environment`

- Verify required env vars from `omnia.env`
- Verify IP address is assigned to a local interface
- Verify hostname and domain match configuration
- Verify `omnia.sh` setup completed
- No credentials or infrastructure changes

### Step 4: Prepare (tag: prepare)

Roles: `deploy_minio`, `deploy_registry`

- Deploy MinIO S3 via Podman Quadlet (if provider=minio)
- Deploy local OCI container registry via Podman Quadlet
- Install and configure `regctl` for image verification (idempotent)
- Create S3 buckets: `boot-images`, `efi-images`
- Open firewall ports: 9000 (S3 API), 9001 (MinIO console), 5000 (registry)

### Step 5: Build (tag: build / execute)

Roles: `fetch_build_packages`, `build_os_images`

- Dual-mode package resolution:
  - **Config mode**: load `package_groups.yml` -> `base_image_packages` + `compute_images_dict`
    - Functional groups derived from `package_groups.yml` keys (no separate list needed)
    - OS type and version from `os` / `os_version` fields in `package_groups.yml`
  - **Catalog mode**: parse catalog JSON via `parse_catalog` module -> same output shape
    - Layer classification by **name** (not component membership)
    - Baseos layers -> `base_image_packages`; compute layers -> `compute_images_dict`
    - OS type (`cluster_os_type`) extracted from baseos group's `os` field
    - OS version (`cluster_os_version`) extracted from baseos group's `os_version` field
- Build base OS image (OpenCHAMI image-builder or image-thrillhouse)
- Build compute images per functional group via `image_build_orchestrator` (concurrency control)
  - `_orchestrator_cmds` defensively initialized before build loop
- Skip compute builds when `compute_images_dict` is empty
- Verify pushed images via `regctl manifest`
- Upload artifacts to S3 (boot-images + efi-images buckets)
- Write `build_status.yml` with per-group S3 artifact paths

#### AArch64 Build Flow

When `aarch64_inventory_host_ip` is set in `image_build_config.yml`:

1. **SSH setup** (runs on localhost): generate SSH key, update `known_hosts`, `ssh-copy-id`
2. **Validate host**: ping check, dynamic inventory group creation
3. **Prepare node** (runs on aarch64 node via SSH): install Podman, create work dirs,
   pull builder image (Pulp -> DockerHub fallback), install regctl
4. **Build**: run image-builder on the aarch64 node with the same config/repos
5. **Write status**: aarch64 results merged into `build_status.yml`

### Step 6: Cleanup (tag: cleanup, opt-in only)

Role: `cleanup_build_artifacts`

- Stop and remove MinIO + Registry containers
- Remove build artifacts, credentials, S3 data
- Remove firewall ports and systemd entries
- Remove `build_status.yml`

### Step 7: Cleanup Images (tag: cleanup_images, opt-in only)

- Delete images from S3 and registry (by pattern or all)
- Supports `cleanup_image_pattern` extra var for selective deletion
- Supports `skip_approval=true` for automation

---

## Playbook Structure

```
playbooks/
+-- image_build_manager.yml          # Top-level orchestrator (all tag routing)
+-- build/
|   +-- build_image_x86_64.yml       # x86_64 image build
|   +-- build_image_aarch64.yml      # aarch64 image build (SSH to ARM node)
|   +-- write_build_status.yml       # Write build_status.yml output
+-- cleanup/
|   +-- cleanup_image_build_manager.yml  # Full cleanup
|   +-- cleanup_images.yml           # Image-only cleanup
+-- credentials/
|   +-- get_build_credentials.yml    # Standalone credential collection
+-- precheck/
|   +-- precheck_environment.yml     # Environment validation
+-- prepare/
|   +-- prepare_image_build_manager.yml  # Deploy MinIO + Registry
+-- rollback/
|   +-- rollback_image_build_manager.yml # Placeholder
+-- upgrade/
|   +-- upgrade_image_build_manager.yml  # Placeholder
+-- validate/
    +-- validate_image_build_config.yml  # Config validation (L1 + L2)
```

## Role Dependency Graph

```
image_build_setup
       |
       +---> validate_image_build_input
       |
       +---> collect_build_credentials
       |
       +---> precheck_environment
       |
       +---> deploy_minio + deploy_registry (+ regctl install)
       |
       +---> fetch_build_packages ---> build_os_images ---> write_build_status
       |     (config or catalog)       (x86_64 + aarch64)
       |
       +---> cleanup_build_artifacts / cleanup_images
```

## Data Contract

### Inputs

| File | Source | Purpose |
|------|--------|---------|
| `image_build_config.yml` | `input/project_default/` | S3, build mode, build params |
| `image_build_credentials.yml` | Generated by `collect_build_credentials` | S3 keys, aarch64 SSH password (vault-encrypted) |
| `repo_status.yml` | repo_manager output | RPM repo URLs, OS metadata |
| `package_groups.yml` | `input/project_default/` | OS metadata + group-to-RPM mapping (config mode) |
| `catalog_rhel.json` | `CATALOG_FILE_PATH` env var | Catalog JSON (catalog mode) |

### Outputs

| File | Location | Purpose |
|------|----------|---------|
| `build_status.yml` | `output/<project>/` | S3 artifact paths per functional group |

## Validation

### Schema Validation (L1)

| Schema | Validates |
|--------|-----------|
| `image_build_config.json` | image_build_config.yml structure |
| `image_build_credentials.json` | image_build_credentials.yml structure |
| `catalog.json` | Catalog JSON structure (when catalog mode) |

### Logic Validation (L2)

| Validator | Checks |
|-----------|--------|
| `image_build_config_validator` | S3 provider/endpoint consistency, aarch64 host/user, build timeout |
| `image_build_credentials_validator` | S3 access keys (powerscale), aarch64 SSH password |
| `catalog_validator` | Structure: layers have name/components, groups is dict |

## Key Design Decisions

1. **Standalone domain** -- no dependency on other domains at code level
2. **Contract-based** -- reads `repo_status.yml`, writes `build_status.yml`
3. **Dual-mode package resolution** -- `config` (manual `package_groups.yml`) or `catalog` (catalog JSON)
4. **Bare-metal only** -- no container or Omnia core required for playbook
5. **Layer-name classification** -- baseos vs compute determined by layer name prefix, not component membership
6. **Dual builder support** -- `image-builder` (standard) or `image-thrillhouse` (next-gen)
7. **Guaranteed regctl** -- installed by `deploy_registry`, used unconditionally for verification
8. **Catalog validation** -- structure checks when `functional_groups_source: "catalog"`
9. **AArch64 separation of concerns** -- SSH setup on localhost, node prep via SSH, build on remote node
