# BuildStream Domain — Output Contract

> **Version:** Omnia 3.0 (Plan 1 v12)
> **Owner:** Rajesh
> **Last updated:** Jul 2025

This document defines every output artifact the BuildStream domain
produces. Downstream domains and operators reference this contract to
understand what is available after a successful `buildstream.yml` run.

---

## 1  Status File

| File | Location (domain-local) | NFS runtime path |
|------|------------------------|------------------|
| `buildstream_status.yml` | `src/build_stream/output/buildstream_status.yml` | `/opt/omnia/output/buildstream/buildstream_status.yml` |

### 1.1  Schema

```yaml
---
# /opt/omnia/output/buildstream/buildstream_status.yml
overall_status: "prepared"          # prepared | running | failed

# --- GitLab Endpoints ---
gitlab_host: "10.0.0.50"           # IP where GitLab CE is deployed
gitlab_https_port: 443             # HTTPS port
gitlab_url: "https://10.0.0.50:443"  # Full GitLab HTTPS URL

# --- BuildStream Manager (BSM) API ---
build_stream_host: "10.0.0.100"   # IP where BSM API runs (OIM server)
build_stream_port: 8010           # BSM API listen port
bsm_api_url: "https://10.0.0.100:8010"  # Full BSM API base URL
```

### 1.2  Field Reference

| Field | Type | Description | Consumer |
|-------|------|-------------|----------|
| `overall_status` | enum | `prepared` — infra is up; `running` — pipeline active; `failed` — setup error. | Any domain checking BuildStream readiness. |
| `gitlab_host` | string (IP) | IP address of the deployed GitLab CE instance. | Operators, CI/CD runners, build_manager (if catalog push is via GitLab). |
| `gitlab_https_port` | int | HTTPS port GitLab listens on. | Operators, GitLab API consumers. |
| `gitlab_url` | string (URL) | Fully qualified HTTPS URL for GitLab. Ready to use in browser or API calls. | Operators, downstream automation. |
| `build_stream_host` | string (IP) | IP of the BSM FastAPI server. | Operators, playbook-watcher, CI/CD pipelines. |
| `build_stream_port` | int | TCP port BSM listens on. | Operators, playbook-watcher, CI/CD pipelines. |
| `bsm_api_url` | string (URL) | Full base URL for the BSM REST API. | CI/CD pipelines (`.gitlab-ci-build.yml`, `.gitlab-ci-deploy.yml`), monitoring. |

---

## 2  BSM REST API Endpoints

Once `buildstream_status.yml` reports `overall_status: prepared`, the
following REST APIs are available at `bsm_api_url`:

| Method | Endpoint | Purpose | Typical Consumer |
|--------|----------|---------|------------------|
| `GET` | `/health` | Health check / readiness probe | Monitoring, pre-checks |
| `POST` | `/api/v1/build` | Trigger an OS image build | GitLab CI build pipeline |
| `POST` | `/api/v1/deploy` | Deploy built images to nodes | GitLab CI deploy pipeline |
| `POST` | `/api/v1/boot` | Boot nodes from deployed images | GitLab CI deploy pipeline |
| `POST` | `/api/v1/validate` | Validate booted nodes | GitLab CI deploy pipeline |
| `GET` | `/api/v1/jobs` | List / query job status | Operators, dashboards |
| `GET` | `/api/v1/jobs/{id}` | Get specific job details | CI/CD, operators |
| `POST` | `/api/v1/catalog/parse` | Parse and validate catalog JSON | Catalog management |
| `PUT` | `/api/v1/artifacts` | Upload deployment artifacts (PXE mapping) | GitLab CI deploy pipeline |
| `GET` | `/api/v1/images` | List built images and their status | Operators, dashboards |
| `POST` | `/api/v1/cleanup` | Clean up stale jobs and artifacts | Scheduled cron, operators |

---

## 3  GitLab CI/CD Artifacts

After `setup_gitlab.yml` completes, the following GitLab resources are
available at `gitlab_url`:

| Resource | Path | Description |
|----------|------|-------------|
| Omnia Catalog Project | `/{gitlab_project_name}` (default: `/omnia-catalog`) | Git repository holding the catalog JSON and CI/CD pipelines. |
| Build Pipeline | `.gitlab-ci-build.yml` | Triggered on catalog changes → builds OS images → creates ImageGroup records via BSM API. |
| Deploy Pipeline | `.gitlab-ci-deploy.yml` | Triggered on `pxe_mapping_file.csv` changes → uploads artifacts → calls `/deploy`, `/boot`, `/validate` APIs. |
| Container Registry | `gitlab_url:5050` | GitLab's built-in container registry (if enabled). |

---

## 4  Container Artifacts

| Container | Image Name | Port | Purpose |
|-----------|-----------|------|---------|
| `omnia_build_stream` | `omnia_build_stream:latest` | `8010` (configurable) | BSM FastAPI server — orchestrates builds, deploys, validations. |

Built from: `src/build_stream/containers/omnia_build_stream/Containerfile`

---

## 5  Log Artifacts

| Log | Path | Description |
|-----|------|-------------|
| Ansible playbook log | `/opt/omnia/log/core/playbooks/buildstream.log` | Ansible output from `buildstream.yml` and sub-playbooks. |
| BSM API log | `/opt/omnia/log/build_stream/build_stream.log` | FastAPI application log (via `log_secure_info`). |
| Per-job logs | `/opt/omnia/log/build_stream/jobs/{job_id}.log` | Individual job execution logs. |
| Playbook-watcher log | `/opt/omnia/log/build_stream/playbook_watcher.log` | Watcher service log (systemd). |

---

## 6  Downstream Consumers

| Consumer | What they read | How |
|----------|---------------|-----|
| **Operators** | `gitlab_url`, `bsm_api_url` | Manual access — browser / curl. |
| **build_manager** | `bsm_api_url` (optional) | If build_manager triggers BSM for image lifecycle. |
| **CI/CD runners** | `bsm_api_url` | GitLab runners call BSM REST API during pipeline stages. |
| **playbook-watcher** | `build_stream_host`, `build_stream_port` | Watches for playbook execution requests and routes to BSM. |
| **Monitoring / alerting** | `/health` endpoint | Liveness / readiness probes. |

---

## 7  Lifecycle States

The `overall_status` field in `buildstream_status.yml` transitions as:

```
 ┌──────────┐     prepare_buildstream.yml     ┌──────────┐
 │ (absent) │ ──────────────────────────────► │ prepared │
 └──────────┘                                 └────┬─────┘
                                                   │
                                          setup_gitlab.yml
                                                   │
                                              ┌────▼─────┐
                                              │ running  │
                                              └────┬─────┘
                                                   │
                                           (on error)
                                                   │
                                              ┌────▼─────┐
                                              │  failed  │
                                              └──────────┘
```
