# Omnia GitLab CI/CD API Integration - Implementation Specification

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Deployment Modes](#deployment-modes)
4. [Input Requirements](#input-requirements)
5. [Directory Structure](#directory-structure)
6. [CI/CD Pipeline Workflow](#cicd-pipeline-workflow)
7. [Playbook Reference](#playbook-reference)
8. [API Integration](#api-integration)
9. [Usage Guide](#usage-guide)
10. [Known Issues](#known-issues)

---

## Overview

This specification details the integration of GitLab CI/CD with Omnia Infrastructure Manager (OIM) API server to automate software catalog-driven image building and deployment workflows.

### Integration Objective
- Automatically trigger CI/CD pipelines when `software_catalog.json` changes
- Execute Omnia workflows via REST API calls from GitLab
- Build, validate, and deploy stateless images to compute nodes
- Support both client-hosted and Omnia-hosted GitLab modes

### Key Components
| Component | Role |
|-----------|------|
| Client Repository | Stores software catalog JSON files |
| GitLab CI/CD | Orchestrates pipeline execution via API calls |
| OIM API Server | Translates API calls to Omnia backend functionality |
| Omnia Backend | Executes Ansible playbooks and manages infrastructure |

---

## Architecture

### High-Level Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client Repository                            │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  software_catalog.json                                      │     │
│  │  (Defines OS, packages, configs for compute nodes)          │     │
│  └────────────────────────────────────────────────────────────┘     │
│                             │                                        │
│                             │ Commit/Push (1)                        │
│                             ▼                                        │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  GitLab Repository                                          │     │
│  │  - .gitlab-ci.yml (pipeline definition)                     │     │
│  │  - software_catalog.json (tracked)                          │     │
│  └────────────────────────────────────────────────────────────┘     │
└───────────────────────────┼──────────────────────────────────────────┘
                            │
                            │ Triggers on catalog change (2)
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    GitLab CI/CD Pipeline                             │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │ Pipeline Stages:                                            │     │
│  │  1. Prerequisites    → Validate OIM connectivity            │     │
│  │  2. Parse Catalog    → POST /catalog/parse                  │     │
│  │  3. Generate Inputs  → POST /catalog/generate-inputs        │     │
│  │  4. Update Repo      → POST /repo/create, /repo/update      │     │
│  │  5. Build Images     → POST /images/build                   │     │
│  │  6. Validate Images  → POST /images/validate                │     │
│  │  7. Deploy TestBed   → POST /deployments/deploy             │     │
│  │  8. Run Tests        → POST /tests/run                      │     │
│  └────────────────────────────────────────────────────────────┘     │
│                             │                                        │
│                             │ REST API Calls (3)                     │
└─────────────────────────────┼────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       OIM API Server                                 │
│                     (https://oim.example.com)                        │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │
│  │ Authentication  │  │ API Endpoints   │  │ Job Manager     │      │
│  │ - Register      │  │ - ParseCatalog  │  │ - Track jobID   │      │
│  │ - Token         │  │ - GenerateInput │  │ - Status checks │      │
│  └─────────────────┘  │ - CreateRepo    │  └─────────────────┘      │
│                       │ - BuildImage    │                            │
│                       │ - ValidateImage │                            │
│                       │ - DeployImage   │                            │
│                       └─────────────────┘                            │
│                              │                                       │
│                              │ Invokes (4)                           │
└──────────────────────────────┼───────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Omnia Backend                                  │
│              (Ansible Playbooks + Input Files)                       │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │ Ansible Playbooks:                                          │     │
│  │  - parse_software_catalog.yml                               │     │
│  │  - generate_input_files.yml                                 │     │
│  │  - local_repo.yml                                           │     │
│  │  - build_stateless_images.yml                               │     │
│  │  - validate_images.yml                                      │     │
│  │  - deploy_images.yml                                        │     │
│  │  - discovery.yml                                            │     │
│  └────────────────────────────────────────────────────────────┘     │
│                             │                                        │
│                             │ Executes (5)                           │
└─────────────────────────────┼────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Target Infrastructure                            │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Local Repo   │  │ Image Store  │  │ Compute Nodes│               │
│  │ (Pulp)       │  │ (S3/NFS)     │  │ (PXE Boot)   │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow Sequence

```
software_catalog.json
         │
         │ (1) Committed to Repository
         ▼
┌─────────────────┐
│ GitLab Detects  │
│ Change          │
└────────┬────────┘
         │
         │ (2) Triggers CI/CD Pipeline
         ▼
┌─────────────────────────────────────────────────────────┐
│                   Pipeline Stages                        │
│                                                          │
│  Parse Catalog ──► Generate Inputs ──► Update Repo      │
│       │                                     │            │
│       ▼                                     ▼            │
│  jobID + parsed                      Local Pulp repo    │
│  manifests                           with packages       │
│                                             │            │
│                                             ▼            │
│  Build Images ──► Validate Images ──► Deploy TestBed    │
│       │                │                    │            │
│       ▼                ▼                    ▼            │
│  Stateless OS    Validation         Images deployed     │
│  images → S3     report             via PXE boot        │
│                                             │            │
│                                             ▼            │
│                                      Run Test Suites    │
│                                             │            │
│                                             ▼            │
│                                      Test Results       │
└─────────────────────────────────────────────────────────┘
```

---

## Deployment Modes

### Mode 1: Omnia-Hosted GitLab (Container)

**Use Case:**
- Customer does not have GitLab environment
- Internal testing and validation
- Quick PoC deployments

```
┌─────────────────────────────────────────────────┐
│         Omnia-Deployed GitLab Container         │
│            (Deployed via Ansible)               │
│         http://100.10.0.83 (example)            │
│                                                 │
│  Automated Setup:                               │
│  1. Deploy GitLab CE container (Podman)         │
│  2. Configure GitLab via API                    │
│  3. Create Omnia project automatically          │
│  4. Push .gitlab-ci.yml to repo                 │
│  5. Configure webhooks and triggers             │
│  6. Set up API tokens                           │
└─────────────────────────────────────────────────┘
         │
         │ API Calls (Internal Network)
         ▼
┌─────────────────────────────────────────────────┐
│              OIM API Server                     │
│         (Same Infrastructure)                   │
└─────────────────────────────────────────────────┘
```

**Configuration:**
```yaml
gitlab_deployment_mode: "hosted"
gitlab_host: "100.10.0.83"
gitlab_hostname: "gitlab.omnia.dev"
```

### Mode 2: Client-Hosted GitLab (Existing)

**Use Case:**
- Client already has an existing GitLab environment
- Enterprise deployments with existing CI/CD infrastructure

```
┌─────────────────────────────────────────────────┐
│      Client's Existing GitLab Instance          │
│      (http://client-gitlab.example.com)         │
│                                                 │
│  Manual Setup Required:                         │
│  1. Create new project for software catalog     │
│  2. Add software_catalog.json to repo           │
│  3. Create .gitlab-ci.yml (via playbook)        │
│  4. Configure CI/CD trigger on catalog changes  │
│  5. Set up API authentication tokens            │
└─────────────────────────────────────────────────┘
         │
         │ API Calls
         ▼
┌─────────────────────────────────────────────────┐
│              OIM API Server                     │
│         (Customer's Omnia Infrastructure)       │
└─────────────────────────────────────────────────┘
```

**Configuration:**
```yaml
gitlab_deployment_mode: "existing"
gitlab_external_url: "http://client-gitlab.example.com"
gitlab_api_token: "glpat-xxxxxxxxxxxx"
```

---

## Input Requirements

### For Hosted Mode (Fresh Deployment)

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `gitlab_host` | IP address of target server | Yes | - |
| `gitlab_hostname` | Hostname for GitLab | No | gitlab.omnia.dev |
| `gitlab_http_port` | HTTP port | No | 80 |
| `gitlab_https_port` | HTTPS port | No | 443 |
| `gitlab_ssh_port` | SSH port for Git | No | 2424 |
| `gitlab_use_https` | Enable HTTPS | No | false |
| `gitlab_config_path` | Config volume path | No | /srv/gitlab/config |
| `gitlab_logs_path` | Logs volume path | No | /srv/gitlab/logs |
| `gitlab_data_path` | Data volume path | No | /srv/gitlab/data |
| `gitlab_min_storage_gb` | Minimum storage (GB) | No | 20 |
| `gitlab_min_memory_gb` | Minimum memory (GB) | No | 4 |
| `gitlab_min_cpu_cores` | Minimum CPU cores | No | 2 |

### For Existing Mode (Integration)

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `gitlab_external_url` | GitLab instance URL | Yes | - |
| `gitlab_api_token` | Personal Access Token (api scope) | Yes | - |
| `gitlab_namespace` | Project namespace/group | No | root |
| `gitlab_project_name` | Project name | No | omnia-software-catalog |
| `gitlab_project_visibility` | Project visibility | No | private |

### Common Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `gitlab_deployment_mode` | "hosted" or "existing" | Yes | hosted |
| `oim_api_url` | OIM API server URL | Yes | - |
| `gitlab_trigger_description` | Webhook trigger description | No | Omnia Software Catalog Webhook |
| `software_catalog_file` | Catalog file name | No | software_catalog.json |

---

## Directory Structure

```
omnia/
├── input/
│   └── gitlab_config.yml          # User inputs for GitLab deployment
├── gitlab/
│   ├── gitlab_config.yml          # Hosted mode playbook (Podman)
│   ├── gitlab_integrate.yml       # Existing mode playbook (integration)
│   └── roles/                     # Future role-specific logic
├── docs/
│   └── gitlab_api_integration.md  # This specification
└── examples/
    └── software_config_template/  # Sample catalog templates
```

---

## CI/CD Pipeline Workflow

### Pipeline Stages

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Prerequisites│──►│ Parse        │──►│ Generate     │──►│ Update       │
│              │   │ Catalog      │   │ Inputs       │   │ Repository   │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
                                                                │
┌──────────────────────────────────────────────────────────────┘
│
▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Build        │──►│ Validate     │──►│ Deploy       │──►│ Run          │
│ Images       │   │ Images       │   │ TestBed      │   │ Tests        │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

### Stage Details

| Stage | API Endpoint | Input | Output |
|-------|--------------|-------|--------|
| Prerequisites | `/health` | - | Connectivity status |
| Parse Catalog | `/catalog/parse` | software_catalog.json | jobID + parsed manifests |
| Generate Inputs | `/catalog/generate-inputs` | jobID | Omnia input files |
| Update Repository | `/repo/create`, `/repo/update` | jobID | Local Pulp repo |
| Build Images | `/images/build` | jobID | Image IDs |
| Validate Images | `/images/validate` | Image IDs | Validation report |
| Deploy TestBed | `/deployments/deploy` | Image IDs | Deployment ID |
| Run Tests | `/tests/run` | Deployment ID | Test results |

---

## Playbook Reference

### gitlab_config.yml (Hosted Mode)

**Purpose:** Deploy GitLab CE container via Podman

**Stages:**
1. Prerequisites Validation (memory, storage, CPU)
2. Install Podman
3. Create Storage Directories
4. Configure Firewall
5. Build GitLab Configuration
6. Stop Existing Container
7. Pull and Run GitLab Container
8. Wait for Initialization
9. Retrieve Credentials
10. Display Summary

**Usage:**
```bash
ansible-playbook omnia/gitlab/gitlab_config.yml
```

### gitlab_integrate.yml (Existing Mode)

**Purpose:** Integrate with existing GitLab instance

**Stages:**
1. Validate GitLab Connectivity
2. Check/Create Project
3. Create Pipeline Trigger
4. Push CI/CD Files
5. Display Summary

**Usage:**
```bash
ansible-playbook omnia/gitlab/gitlab_integrate.yml
```

---

## API Integration

### Authentication Flow

```
┌─────────────┐         ┌─────────────┐
│   GitLab    │         │     OIM     │
│   Pipeline  │         │ API Server  │
└──────┬──────┘         └──────┬──────┘
       │                       │
       │ POST /auth/register   │
       ├──────────────────────►│
       │                       │
       │ client_id, secret     │
       │◄──────────────────────┤
       │                       │
       │ POST /auth/token      │
       ├──────────────────────►│
       │                       │
       │ Bearer token          │
       │◄──────────────────────┤
       │                       │
       │ API calls with token  │
       ├──────────────────────►│
       │                       │
```

### Error Handling

- **Retry Strategy:** Configurable attempts/delay (default: 3 attempts, 30s delay)
- **Structured Logging:** Each stage logs request/response metadata
- **Artifacts:** API responses stored as CI artifacts
- **Alerts:** Pipeline fails on non-recoverable API errors

---

## Usage Guide

### Hosted Mode Deployment

1. **Configure inputs:**
   ```bash
   vi omnia/input/gitlab_config.yml
   ```
   Set:
   ```yaml
   gitlab_deployment_mode: "hosted"
   gitlab_host: "100.10.0.83"
   ```

2. **Run deployment playbook:**
   ```bash
   ansible-playbook omnia/gitlab/gitlab_config.yml
   ```

3. **Retrieve credentials from output**

4. **Login to GitLab UI and create API token**

5. **Update inputs with token:**
   ```yaml
   gitlab_api_token: "glpat-xxxxxxxxxxxx"
   gitlab_deployment_mode: "existing"
   ```

6. **Run integration playbook:**
   ```bash
   ansible-playbook omnia/gitlab/gitlab_integrate.yml
   ```

### Existing Mode Integration

1. **Configure inputs:**
   ```bash
   vi omnia/input/gitlab_config.yml
   ```
   Set:
   ```yaml
   gitlab_deployment_mode: "existing"
   gitlab_external_url: "http://gitlab.example.com"
   gitlab_api_token: "glpat-xxxxxxxxxxxx"
   ```

2. **Run integration playbook:**
   ```bash
   ansible-playbook omnia/gitlab/gitlab_integrate.yml
   ```

3. **Add software_catalog.json to repository**

4. **Commit changes to trigger pipeline**

---

## Known Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Browser cache | Login fails with correct credentials | Clear browser cache |
| Rapid actions | 500 errors, system hangs | Wait a few seconds between actions |
| Resource limits | "Resource temporarily unavailable" | Increase ulimit values in gitlab_config.yml |
| Service instability | Project creation hangs | Check `gitlab-ctl status`, restart services |

### Troubleshooting Commands

```bash
# Check container status
sudo podman ps -a

# Check GitLab services
sudo podman exec -it gitlab gitlab-ctl status

# View logs
sudo podman logs --tail 100 gitlab

# Restart services
sudo podman exec -it gitlab gitlab-ctl restart

# Restart container
sudo podman restart gitlab
```

---

## References

- [GitLab CI/CD Documentation](https://docs.gitlab.com/ee/ci/)
- [GitLab API Documentation](https://docs.gitlab.com/ee/api/)
- [Omnia Documentation](https://omnia-doc.readthedocs.io/)
