# BuildStream Domain — Input Contract

> **Version:** Omnia 3.0 (Plan 1 v12)
> **Owner:** Rajesh
> **Last updated:** Jul 2025

This document defines every input the BuildStream domain requires.
Other domains and operators reference this contract to understand what
must be supplied before running `build_stream.yml`.

---

## 1  Configuration File

| File | Location (domain-local) | NFS runtime path |
|------|------------------------|------------------|
| `build_stream_config.yml` | `src/build_stream/input/build_stream_config.yml` | `/opt/omnia/input/project_default/build_stream/build_stream_config.yml` |

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

### 1.3  Pipeline Log Observability (ER-BSM-003)

Pipeline execution logs are served by the BSM API endpoint
`GET /api/v1/jobs/{job_id}/logs` and previewed in the GitLab CI job console.
Logs exist **only for stages that run an Ansible playbook**; other stages
(e.g. create-job, parse-catalog, upload) have no execution log.

The operator-tunable parameters live in **Section 5** of
`build_stream_config.yml` (`$OMNIA_DATA_PATH/build_stream/input/<project>/`).
All are optional and are read when the `omnia_build_stream` container starts
(re-run the build_stream playbook after a change; it also refreshes the GitLab CI/CD variable).
They are validated by `validate_build_stream_config` (JSON schema + L2) and
again at load time; an invalid value is rejected as a whole and the
`build_stream.ini` / built-in defaults stay in effect.

| Parameter (`build_stream_config.yml`) | Type | Required | Default | Description |
|---|---|---|---|---|
| `log_tail_lines_default` | int (1..`log_tail_lines_max`) | Optional | `50` | Lines returned per stage when `tail_lines` is omitted. |
| `log_tail_lines_max` | int (1..10000) | Optional | `10000` | Upper bound accepted for the `tail_lines` query parameter. |
| `max_log_response_bytes` | int (1024..52428800) | Optional | `10485760` | Maximum log bytes returned per stage (`full=true` or tail); 10 MiB. |
| `log_ci_preview_lines` | int (1..`log_tail_lines_max`) | Optional | `50` | Execution-log lines previewed in the GitLab CI job console. Pushed to the GitLab project as CI/CD variable `BSM_LOG_TAIL_LINES` on each build_stream run. |
| `log_query_rate_limit` | int (>=1) | Optional | `60` | Per-OAuth-client log-query requests allowed per minute (429 when exceeded). |
| `log_query_max_concurrent` | int (>=1) | Optional | `5` | Log-query requests served concurrently across all clients (503 + `Retry-After`). |

Precedence: `build_stream_config.yml` > `[log_query]` in
`build_stream.ini` (advanced; also holds `log_root`, the container path of the
published per-job logs, default `${OMNIA_DATA_PATH}/build_stream/log`) >
built-in defaults.

**CI/CD variable** — managed by Omnia, not hand-edited. The GitLab CI pipelines
(`build`, `cadence`, `deploy`) preview the last N execution-log lines in the job
console on completion (playbook stages only):

| CI/CD variable | Source | Default | Description |
|---|---|---|---|
| `BSM_LOG_TAIL_LINES` | `log_ci_preview_lines` in `build_stream_config.yml` | `50` | Lines previewed in the job console (`after_script`). Set on the GitLab project by `set_pipeline_variables`; a per-pipeline-run variable of the same name still overrides it. |

---

## 2  Credentials

Credentials are retrieved via the shared `credential_utility` with the
following tags:

| Tag | Type | Credentials | Notes |
|-----|------|-------------|-------|
| `gitlab` | mandatory + optional | `gitlab_root_password`; `docker_username`, `docker_password` | Root password is mandatory. Docker creds are optional (for pulling images from private registries). |
| `build_stream` | mandatory + conditional | `gitlab_root_password`; `build_stream_auth_*`, `postgres_user`, `postgres_password` | GitLab root password is mandatory. BSM auth and Postgres creds are conditional on `enable_build_stream`. |

Credential source files:

| File | Scope | Format |
|------|-------|--------|
| `build_stream/build_stream_credentials.yml` | BuildStream domain | Ansible Vault encrypted — postgres creds + GitLab root password + BSM OAuth auth |

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
| PostgreSQL available for BSM state | `prepare_build_stream.yml` |

---

## 5  File Origins (Migration Map)

| New (domain-local) | Old (pre-3.0 location) | Action |
|--------------------|----------------------|--------|
| `input/build_stream_config.yml` | `input/build_stream_config.yml` + `input/gitlab_config.yml` | **Merged** — both files consolidated into one. |
| `roles/hosted_gitlab/` | `playbooks/gitlab/roles/hosted_gitlab/` | **Copied** |
| `roles/cleanup_gitlab/` | `playbooks/gitlab/roles/cleanup_gitlab/` | **Copied** |
| `roles/gitlab_passwordless_ssh/` | `playbooks/gitlab/roles/gitlab_passwordless_ssh/` | **Copied** |
| `containers/omnia_build_stream/` | `containers/omnia_build_stream/` | **Copied** |
