# Omnia CI/CD Pipeline Documentation

Automated deployment, cleanup, and validation testing of Omnia across one or more target servers, driven entirely from GitLab CI/CD.

---

## 📚 Documentation Guide

Choose the guide that matches your needs:

### 🚀 **New to the Pipeline?**
Start here → **[Quick Start Guide](QUICKSTART.md)**
- 5-minute setup walkthrough
- Step-by-step instructions
- Common tasks

### 🔐 **Setting Up OpenBao?**
→ **[OpenBao Setup Guide](OPENBAO_SETUP.md)**
- Install and configure OpenBao
- Set up secrets engine
- Configure JWT authentication for GitLab
- Troubleshoot OpenBao issues

### 🎯 **Choosing Deployment Strategy?**
→ **[Pipeline Modes & Domains](PIPELINE_MODES.md)**
- Understand `default`, `deploy`, and `cleanup` modes
- Select which domains to run
- Real-world deployment scenarios
- Pipeline stages reference

### ⚙️ **Configuring Everything?**
→ **[Configuration Reference](CONFIGURATION.md)**
- Complete `pipeline_config.yml` reference
- All CI/CD variables explained
- Multi-cluster deployment
- Advanced features
- All setup script commands

### 🔧 **Troubleshooting Issues?**
→ **[Troubleshooting Guide](TROUBLESHOOTING.md)**
- Common problems and solutions
- SSH connectivity issues
- OpenBao authentication
- Ansible deployment errors
- Test failures
- Getting help

---

## Overview

The Omnia CI/CD pipeline automates the complete lifecycle of Omnia deployments:

- **Setup** — Clones Omnia on the target server, copies configuration, builds the Python virtual environment
- **Cleanup** — Removes previous deployments for selected domains
- **Deploy** — Fetches credentials from OpenBao, copies input files, encrypts credentials with ansible-vault, and runs Ansible playbooks for each domain
- **Test** — Validates each deployed domain with automated test suites
- **Report** — Generates a summary and sends email notifications

Each cluster runs as a completely independent child pipeline. If one cluster fails, the others continue unaffected.

---

## Prerequisites

| Requirement | Details |
|---|---|
| **GitLab** | Version 15.7+ with CI/CD pipelines enabled and a registered runner |
| **Target server** | RHEL/Rocky Linux with SSH access (port 22) and root or sudo user |
| **OpenBao** | Installed, unsealed, and network-reachable from the GitLab Runner on port 8200 |
| **Python** | 3.x on the machine running `setup_gitlab_project.py` |
| **Python packages** | `pip install pyyaml requests` |

---

## Quick Links

### For Different Roles

| Role | Start Here |
|---|---|
| **DevOps Engineer** | [Quick Start](QUICKSTART.md) → [Configuration Reference](CONFIGURATION.md) |
| **System Administrator** | [OpenBao Setup](OPENBAO_SETUP.md) → [Quick Start](QUICKSTART.md) |
| **Infrastructure Team** | [Pipeline Modes](PIPELINE_MODES.md) → [Configuration Reference](CONFIGURATION.md) |
| **Troubleshooting Issues** | [Troubleshooting Guide](TROUBLESHOOTING.md) |

### Common Tasks

- **Deploy to a single server** → [Quick Start](QUICKSTART.md)
- **Deploy to multiple servers** → [Configuration Reference](CONFIGURATION.md#multi-cluster-deployment)
- **Redeploy a single domain** → [Pipeline Modes](PIPELINE_MODES.md#scenario-2-redeploy-only-repo_manager-after-changing-pulp-credentials)
- **Clean up and start fresh** → [Pipeline Modes](PIPELINE_MODES.md#scenario-5-full-cleanup-of-everything-on-the-target)
- **Rotate credentials** → [Configuration Reference](CONFIGURATION.md#rotating-credentials)
- **Fix SSH connectivity** → [Troubleshooting](TROUBLESHOOTING.md#pipeline-fails-at-initialization)
- **Fix OpenBao issues** → [Troubleshooting](TROUBLESHOOTING.md#openbao-server-is-not-reachable)

---

## Architecture

### Pipeline Flow

```
Parent Pipeline (.gitlab-ci.yml)
    ↓
    └─→ Child Pipeline 1 (.gitlab-ci-cluster.yml) for cluster1
    │   ├─ initialization
    │   ├─ setup_environment
    │   ├─ cleanup_<domains>
    │   ├─ deploy_<domains>
    │   ├─ test_<domains>
    │   └─ summary
    │
    └─→ Child Pipeline 2 (.gitlab-ci-cluster.yml) for cluster2
        ├─ initialization
        ├─ setup_environment
        ├─ cleanup_<domains>
        ├─ deploy_<domains>
        ├─ test_<domains>
        └─ summary
```

Each cluster runs independently. If cluster1 fails, cluster2 continues.

### Credential Flow

```
OpenBao (Vault-compatible)
    ↓
GitLab Runner (JWT authentication)
    ↓
Pipeline Job (fetches secrets)
    ↓
Target Server (ansible-vault encrypted)
```

No static secrets are stored in GitLab. Each pipeline job gets a short-lived JWT token.

---

## Key Concepts

### Pipeline Modes

- **`default`** — Full cycle: setup → cleanup → deploy → test
- **`deploy`** — Deploy only (fast, for incremental updates)
- **`cleanup`** — Tear down domains or entire environment

### Domains

- **repo_manager** — Pulp-based package and repository management
- **image_build_manager** — Container image building and registry
- **orchestrator** — Kubernetes and container orchestration
- **telemetry** — Monitoring, logging, and observability

You can run all domains or select specific ones using regex patterns.

### Clusters

Deploy to one or more target servers independently. Each cluster has its own:
- Connection details (IP, username, password)
- Pipeline mode and domain selection
- Test mode and other settings

---

## File Structure

```
test/pipeline/
├── docs/
│   ├── README.md                    ← You are here
│   ├── QUICKSTART.md                ← Start here for quick setup
│   ├── OPENBAO_SETUP.md             ← OpenBao configuration
│   ├── PIPELINE_MODES.md            ← Deployment strategies
│   ├── CONFIGURATION.md             ← Complete reference
│   └── TROUBLESHOOTING.md           ← Common issues & solutions
├── .gitlab-ci.yml                   ← Parent pipeline (multi-cluster)
├── .gitlab-ci-cluster.yml           ← Child pipeline (per-cluster stages)
├── setup_gitlab_project.py          ← Setup script
├── pipeline_config.yml              ← Your configuration (create this)
└── clusters/
    ├── cluster1/
    │   ├── cluster.env              ← Connection details
    │   └── inputs/
    │       ├── omnia.env            ← Omnia environment
    │       ├── repo_manager/        ← Domain configs
    │       ├── orchestrator/
    │       ├── image_build_manager/
    │       ├── telemetry/
    │       └── test/                ← Test configs
    └── cluster2/
        └── ...
```

---

## Getting Started

### Step 1: Complete OpenBao Setup
→ [OpenBao Setup Guide](OPENBAO_SETUP.md)

### Step 2: Follow Quick Start
→ [Quick Start Guide](QUICKSTART.md)

### Step 3: Customize Your Deployment
→ [Pipeline Modes & Domains](PIPELINE_MODES.md)

### Step 4: Reference Configuration
→ [Configuration Reference](CONFIGURATION.md)

### Step 5: Troubleshoot Issues
→ [Troubleshooting Guide](TROUBLESHOOTING.md)

---

## Support & Help

- **Documentation:** Start with the [Quick Start Guide](QUICKSTART.md)
- **Configuration Help:** See [Configuration Reference](CONFIGURATION.md)
- **Deployment Strategies:** Check [Pipeline Modes & Domains](PIPELINE_MODES.md)
- **Troubleshooting:** Visit [Troubleshooting Guide](TROUBLESHOOTING.md)
- **OpenBao Issues:** See [OpenBao Setup Guide](OPENBAO_SETUP.md)

---

## License

Licensed under the Apache License, Version 2.0. See the Omnia project for full license text.
