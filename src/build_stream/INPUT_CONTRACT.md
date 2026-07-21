# BuildStream Domain — Input Contract

> **Version:** Omnia 3.0 (Plan 1 v12)
> **Owner:** Rajesh
> **Last updated:** Jul 2025

This document defines every input the BuildStream domain requires.
Other domains and operators reference this contract to understand what
must be supplied before running `buildstream.yml`.

---

## 1  Configuration File

| File | Location (domain-local) | NFS runtime path |
|------|------------------------|------------------|
| `buildstream_config.yml` | `src/build_stream/input/buildstream_config.yml` | `/opt/omnia/input/project_default/buildstream/buildstream_config.yml` |

### 1.1  BuildStream Manager (BSM) Settings

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `enable_build_stream` | bool | **Mandatory** | `false` | Master switch — when `false` the entire domain is skipped. |
| `build_stream_host_ip` | string (IP) | **Mandatory** | `""` | Public or admin IP of the OIM server hosting the BSM API. |
| `build_stream_port` | int (1-65535) | **Mandatory** | `8010` | TCP port the BSM FastAPI server listens on. |

### 1.2  GitLab Settings

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `gitlab_host` | string (IP) | **Mandatory** | `""` | IP of the target host where GitLab CE will be deployed. Must be reachable from OIM. |
| `gitlab_project_name` | string | Optional | `"omnia-catalog"` | GitLab project name Omnia creates/manages. |
| `gitlab_project_visibility` | enum | Optional | `"private"` | `private` \| `internal` \| `public`. |
| `gitlab_default_branch` | string | Optional | `"main"` | Default branch for repo and API ops. |
| `gitlab_https_port` | int (1-65535) | Optional | `443` | HTTPS port exposed via GitLab NGINX. Must not conflict with other services. |
| `gitlab_min_storage_gb` | int | Optional | `20` | Minimum free disk (GB) validated before install. |
| `gitlab_min_memory_gb` | int | Optional | `4` | Minimum RAM (GB). Increase for production. |
| `gitlab_min_cpu_cores` | int | Optional | `2` | Minimum CPU cores. |
| `gitlab_puma_workers` | int | Optional | `2` | Puma web worker count (1-2 per core). |
| `gitlab_sidekiq_concurrency` | int | Optional | `10` | Sidekiq background job concurrency. |

---

## 2  Credentials

Credentials are retrieved via the shared `credential_utility` with the
following tags:

| Tag | Type | Credentials | Notes |
|-----|------|-------------|-------|
| `gitlab` | mandatory + optional | `gitlab_root_password`; `docker_username`, `docker_password` | Root password is mandatory. Docker creds are optional (for pulling images from private registries). |
| `prepare_oim` | conditional | `build_stream_auth_*`, `postgres_user`, `postgres_password` | Required when BSM needs Postgres and OAuth secrets. |

Credential source files:

| File | Scope | Format |
|------|-------|--------|
| `omnia_config_credentials.yml` | All domains | Ansible Vault encrypted |
| `build_stream_oauth_credentials.yml` | BuildStream only | Argon2 hashed BSM auth |

---

## 3  Upstream Domain Dependencies

| Upstream domain | Artifact consumed | Required? | Notes |
|----------------|-------------------|-----------|-------|
| *(none)* | — | — | BuildStream has **no upstream domain pre-checks**. It can run independently. |

---

## 4  Infrastructure Prerequisites

| Prerequisite | Validated by |
|-------------|-------------|
| Target `gitlab_host` is reachable from OIM | `hosted_gitlab/prereq_checks.yml` |
| `gitlab_host` meets min CPU / RAM / disk | `hosted_gitlab/check_oim_prerequisites.yml` |
| SSH access to `gitlab_host` via `provision_password` | credential_utility + `add_host` |
| PostgreSQL available for BSM state | `prepare_buildstream.yml` |

---

## 5  File Origins (Migration Map)

| New (domain-local) | Old (pre-3.0 location) | Action |
|--------------------|----------------------|--------|
| `input/buildstream_config.yml` | `input/build_stream_config.yml` + `input/gitlab_config.yml` | **Merged** — both files consolidated into one. |
| `roles/hosted_gitlab/` | `playbooks/gitlab/roles/hosted_gitlab/` | **Copied** |
| `roles/cleanup_gitlab/` | `playbooks/gitlab/roles/cleanup_gitlab/` | **Copied** |
| `roles/gitlab_passwordless_ssh/` | `playbooks/gitlab/roles/gitlab_passwordless_ssh/` | **Copied** |
| `containers/omnia_build_stream/` | `containers/omnia_build_stream/` | **Copied** |
