# Image Build Manager — Architecture Overview

## System Context

```
                    ┌─────────────────────────────────────────────┐
                    │      Image Build Manager                      │
                    │                                             │
  ┌──────────┐      │  ┌────────────┐  ┌────────────┐  ┌────────┐│      ┌──────────┐
  │ config   │─────▶│  │ Validate   │─▶│ Prepare    │─▶│ Build  ││─────▶│ S3 / OCI │
  │  .yml    │      │  │ (schema +  │  │ (MinIO +   │  │ (base +││      │ Artifacts│
  │ + repo   │      │  │  runtime)  │  │  registry) │  │ compute││      │          │
  │ _status  │      │  └────────────┘  └────────────┘  └────────┘│      └──────────┘
  └──────────┘      └─────────────────────────────────────────────┘
```

## Execution Mode

**Bare-metal** — the only supported execution mode. The playbook runs
directly on the RHEL host via `ansible-playbook`. All tasks execute locally
(`connection: local`) except aarch64 builds which SSH to an ARM node.

## Execution Flow

### 1. Setup (`image_build_setup` role — tag: always)

- Validate tags and tag combinations
- Load and validate `config.yml` — hostname regex, IPv4, absolute path checks
- Set project dirs, host vars
- Validate all prerequisite files exist (fail-fast):
  - `image_build_config.yml`
  - `repo_manager_output_path` directory
  - `repo_status.yml` inside it
  - `functional_group_packages.yml` inside it
- Load `repo_status.yml` → RPM repo URLs, cert paths
- Validate Pulp certificate exists at absolute path
- Build repo lists, set pulp facts, s3_endpoint

### 2. Validate (`--tags validate`)

- Schema validation of `image_build_config.yml` against JSON schema
- Logic validation (S3 provider, aarch64 host, repo_status pre-check)
- No credentials required

### 3. Prepare (`--tags prepare`)

- Collect S3 credentials (interactive prompts, Ansible Vault)
- Deploy MinIO S3 (if provider=minio) via Podman Quadlet
- Deploy local OCI container registry via Podman Quadlet

### 4. Build (`--tags build`)

- Write `functional_groups_config.yml` from `image_build_config.yml`
- Load `functional_group_packages.yml` → `base_image_packages` + `compute_images_dict`
- Fetch Pulp RPM repo URLs from `repo_status.yml`
- Build base OS image (OpenCHAMI image-build)
- Build compute images per functional group (OpenCHAMI image-build)
- Upload to S3 (boot-images + efi-images buckets)
- Write `build_status.yml` with artifact paths

### 5. Cleanup (`--tags cleanup`)

- Stop and remove MinIO + Registry containers
- Remove build artifacts, credentials, S3 data
- Remove firewall ports and systemd entries

## Role Dependency Graph

```
image_build_setup ─────────────────────────────────────────┐
       │                                                   │
       ▼                                                   ▼
validate_image_build_input                    collect_build_credentials
       │                                                   │
       ▼                                                   ▼
validate_build_runtime                        deploy_minio + deploy_registry
       │                                                   │
       ▼                                                   ▼
fetch_build_packages ──────────────────────▶ build_os_images
       │                                                   │
       │                                                   ▼
       │                                     write_build_status
       │
       ▼
cleanup_build_artifacts
```

## Data Contract

### Inputs

| File | Source | Purpose |
|------|--------|---------|
| `config.yml` | User-created (repo root) | Host + project settings |
| `image_build_config.yml` | `input/project_default/` | S3, functional groups, build params |
| `repo_status.yml` | `/opt/omnia/repo_manager/output/<project_name>/` | RPM repo URLs + OS metadata + cert paths |
| `functional_group_packages.yml` | `/opt/omnia/repo_manager/output/<project_name>/` | Functional group → RPM package mapping |

### Outputs

| File | Purpose |
|------|---------|
| `build_status.yml` | S3 artifact paths per functional group |
| Validation logs | `/opt/omnia/image_build_manager/log/<project>/` |

## Key Paths

| Path | Purpose |
|------|---------|
| `/opt/omnia/image_build_manager/` | Shared path — MinIO data, registry, workdir, logs |
| `/opt/omnia/image_build_manager/log/playbooks/` | Ansible playbook logs |
| `/opt/omnia/repo_manager/output/<project_name>/` | Upstream repo_manager output directory |
| `/opt/omnia/pulp/settings/certs/pulp_webserver.crt` | Pulp TLS certificate (read as-is) |

## Key Design Decisions

1. **No `software_config.json`** — replaced by `functional_group_packages.yml`
2. **Bare-metal only** — no container or Omnia core required
3. **Absolute cert paths** — read directly from `repo_status.yml`, no staging
4. **Config uses `host`** — generic key name (not `build_host`), works for all repos
5. **Single mapping file** — `functional_group_packages.yml` is the single source
   of truth for which RPMs go into each image variant
6. **Standalone** — no dependency on `omnia_core` container or mono-repo
