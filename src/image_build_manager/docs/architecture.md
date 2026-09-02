# Image Build Manager -- Architecture

## System Context

```
  repo_status.yml                                                    build_status.yml
  catalog_rhel.json (or package_groups.yml)                          S3 artifacts
  +---------------------+     +-------------------------------------+     +-----------+
  |                     |     |       Image Build Manager            |     |           |
  |  repo_manager       |---->|                                     |---->| provision |
  |  (upstream)         |     |  setup -> validate -> prepare       |     | workflow  |
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

All tags are **mutually exclusive** -- run exactly ONE tag (or none for default flow).

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

### Invalid Tag Combinations

Tags like `prepare + cleanup`, `build + cleanup`, `precheck + build`, etc. are rejected
at startup with a clear error message.

---

## Execution Flow

### Step 0: Setup (tag: always)

- Validate provided tags against supported tags
- Set `skip_build_credentials` flag for tags that don't need credentials
- Determine whether `repo_status.yml` is required (only for build/execute/default flow)
- Load environment variables from `omnia.env`
- Set project directories and host vars
- Set `functional_groups_source` (`config` or `catalog`)
- Validate prerequisite files exist (fail-fast, skipped for cleanup/precheck):
  - `image_build_config.yml` -- always required
  - `repo_status.yml` -- required for build-related tags
  - `package_groups.yml` -- when `functional_groups_source: "config"`
  - `CATALOG_FILE_PATH` -- when `functional_groups_source: "catalog"`
- Load `repo_status.yml` via `parse_repo_status` module (when needed)
- Validate repo manager certificate (if present)

### Step 1: Validate (tag: always, skipped for precheck)

- Schema validation via JSON Schema
- Logic validation (S3 provider, aarch64 host, build timeout)
- Catalog structure validation (when `functional_groups_source: "catalog"`):
  - Schema structure checks (functionallayer, groups, packages)
  - Structure validation: layers have name/components, groups is dict
- No credentials required

### Step 2: Credentials (tag: always, skipped for validate/cleanup/cleanup_images/precheck)

- Prompt for S3 access/secret keys (Ansible Vault encrypted)
- Prompt for aarch64 SSH password (if ARM host configured)
- Output: `input/<project>/image_build_credentials.yml` (vault-encrypted)

### Step 3: Precheck (tag: precheck, opt-in only)

- Verify required env vars from `omnia.env`
- Verify IP address is assigned to a local interface
- Verify hostname and domain match configuration
- Verify `omnia.sh` setup completed
- No credentials or infrastructure changes

### Step 4: Prepare (tag: prepare)

- Deploy MinIO S3 via Podman Quadlet (if provider=minio)
- Deploy local OCI container registry via Podman Quadlet
- Install and configure `regctl` for image verification (idempotent)
- Create S3 buckets: `boot-images`, `efi`
- Open firewall ports: 9000 (S3 API), 9001 (MinIO console), 5000 (registry)

### Step 5: Build (tag: build / execute)

- Dual-mode package resolution:
  - **Config mode**: load `package_groups.yml` -> `base_image_packages` + `compute_images_dict`
    - Functional groups derived from `package_groups.yml` keys (no separate list needed)
    - OS type and version from `os` / `os_version` fields in `package_groups.yml`
  - **Catalog mode**: parse catalog JSON via `parse_catalog` module -> same output shape
    - Layer classification by **name** (not component membership)
    - Baseos layers -> `base_image_packages`; compute layers -> `compute_images_dict`
    - OS type extracted from baseos group's `os` field
    - OS version extracted from baseos group's `os_version` field
- Build base OS image (OpenCHAMI image-builder or image-thrillhouse)
- Build compute images per functional group with concurrency control
- Skip compute builds when `compute_images_dict` is empty
- Verify pushed images via `regctl manifest`
- Upload artifacts to S3 (boot-images + efi-images buckets)
- Write `build_status.yml` with per-group S3 artifact paths

#### AArch64 Build Flow

When `aarch64_inventory_host_ip` is set in `image_build_config.yml`:

1. **SSH setup** (runs on localhost): generate SSH key, update `known_hosts`, `ssh-copy-id`
2. **Validate host**: ping check, dynamic inventory group creation
3. **Prepare node** (runs on aarch64 node via SSH): install Podman, create work dirs,
   pull builder image (Pulp -> DockerHub fallback), copy regctl from OIM
4. **Build**: run image-builder on the aarch64 node with the same config/repos
5. **Write status**: aarch64 results merged into `build_status.yml`

### Step 6: Cleanup (tag: cleanup, opt-in only)

- Stop and remove MinIO + Registry containers
- Remove build artifacts, credentials, S3 data
- Remove firewall ports and systemd entries
- Remove `build_status.yml`

### Step 7: Cleanup Images (tag: cleanup_images, opt-in only)

- Delete images from S3 and registry (by pattern or all)
- Supports `cleanup_image_pattern` extra var for selective deletion
- Supports `skip_approval=true` for automation

---

## Output

### build_status.yml

`build_status.yml` records exact endpoint-relative S3 object paths. Paths include
the `boot-images` bucket, omit the endpoint and `s3://` scheme, and end with a
filename. The layout is selected globally by `image_build_type`.

```yaml
overall_status: "success"

s3_configurations:
  endpoint_url: "http://10.20.0.1:9000"
  bucket: "boot-images"

functional_group_images:
  - x86_64:
    - functional_group: "slurm_node_x86_64"
      kernel: "boot-images/slurm_node_x86_64/rhel-slurm_node_x86_64_omnia_2.3-imgth/10.0/vmlinuz"
      initrd: "boot-images/slurm_node_x86_64/rhel-slurm_node_x86_64_omnia_2.3-imgth/10.0/initramfs.img"
      image: "boot-images/slurm_node_x86_64/rhel-slurm_node_x86_64_omnia_2.3-imgth/10.0/rootfs.squashfs"
```

For `image-builder`, the three fields instead use these exact object shapes:

```text
boot-images/efi-images/<functional_group>/<image_name>-imgbld/vmlinuz-<kernel-version>
boot-images/efi-images/<functional_group>/<image_name>-imgbld/initramfs-<kernel-version>.img
boot-images/<functional_group>/<image_name>-imgbld/<rootfs-filename>
```

### S3 Artifacts

`image-builder`:

```text
boot-images/
+-- efi-images/<functional_group>/<image_name>-imgbld/
|   +-- vmlinuz-<kernel-version>
|   +-- initramfs-<kernel-version>.img
+-- <functional_group>/<image_name>-imgbld/
    +-- <rootfs-filename>
```

`image-thrillhouse`:

```text
boot-images/<functional_group>/<image_name>-imgth/<release>/
+-- vmlinuz
+-- initramfs.img
+-- rootfs.squashfs
```

### Deployed Services

| Service | Ports | Purpose |
|---------|-------|---------|
| MinIO S3 (Podman Quadlet) | 9000 (API), 9001 (Console) | Boot image storage |
| OCI Registry (Podman Quadlet) | 5000 (HTTP) | Image verification |

---

## Validation

### Schema Validation

| Schema | Purpose |
|--------|---------|
| `image_build_config.json` | Main config validation |
| `image_build_credentials.json` | Credential format validation |
| `functional_groups_config.json` | Functional groups config |
| `catalog.json` | Catalog JSON structure (when catalog mode) |

### Logic Validation

| Validator | Checks |
|-----------|--------|
| `image_build_config_validator` | S3 provider/endpoint consistency, aarch64 host/user, build timeout |
| `image_build_credentials_validator` | S3 access keys (powerscale), aarch64 SSH password |
| `catalog_validator` | Structure: layers have name/components, groups is dict |
