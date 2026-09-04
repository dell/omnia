# Omnia CI/CD Pipeline

Automated deployment, cleanup, and validation testing of Omnia across one or
more target servers, driven entirely from GitLab CI/CD.

For the complete step-by-step guide, see [docs/Pipeline_Guide.md](docs/Pipeline_Guide.md).

---

## Overview

This pipeline automates the complete lifecycle of Omnia deployments:

- **Setup** -- Clones Omnia on the target server, copies configuration, builds
  the Python virtual environment
- **Cleanup** -- Removes previous deployments for selected domains
- **Deploy** -- Fetches credentials from OpenBao, copies input files, encrypts
  credentials with ansible-vault, and runs Ansible playbooks for each domain
- **Test** -- Validates each deployed domain with automated test suites
- **Report** -- Generates a summary and sends email notifications

Each cluster runs as a completely independent child pipeline. If one cluster
fails, the others continue unaffected.

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

## Repository Structure

After the setup script creates the GitLab project, the repository looks like
this:

```
.gitlab-ci.yml                          Parent pipeline (triggers per-cluster)
.gitlab-ci-cluster.yml                  Child pipeline (all stages for one cluster)
pipeline_config.yml                     Pipeline configuration (fill this out)
setup_gitlab_project.py                 Script to create/update the GitLab project
send_email.py                           Email notification helper

clusters/cluster1/
  inputs/
    omnia.env                           Omnia environment config
    repo_manager/                       repo_manager input files
    image_build_manager/                image_build_manager input files
    orchestrator/                       orchestrator input files
    telemetry/                          telemetry input files
    test/                               Test configuration files
  catalogs/
    catalog_rhel.json                   Catalog file (optional)
```

---

## Quick Start

1. **Set up OpenBao** -- Install, unseal, store credentials, configure JWT
   auth for GitLab. See the full guide: [OpenBao Configuration](docs/Pipeline_Guide.md#openbao-configuration-and-gitlab-integration)

2. **Fill in `pipeline_config.yml`** -- Set cluster IP, SSH user, OpenBao URL,
   pipeline mode, and domains

3. **Run the setup script:**
   ```bash
   pip install pyyaml requests

   python3 setup_gitlab_project.py --create \
       --gitlab-url https://gitlab.example.com \
       --token glpat-xxxx \
       --project-name omnia-pipeline \
       --config pipeline_config.yml
   ```

4. **Edit input files** in the GitLab repository under
   `clusters/cluster1/inputs/`

5. **Trigger the pipeline** from **CI/CD > Pipelines > Run pipeline**

---

## Pipeline Modes

| Mode | Flow | Use case |
|---|---|---|
| `default` | Setup > Cleanup > Deploy > Test > Summary | First-time deployment or full refresh |
| `deploy` | Deploy > Test > Summary | Incremental updates (skip cleanup) |
| `cleanup` | Cleanup > Summary | Tear down deployed resources |

---

## Domains

| Domain | Purpose |
|---|---|
| **repo_manager** | Pulp-based package and repository management |
| **image_build_manager** | Container image building and registry |
| **orchestrator** | Kubernetes and container orchestration |
| **telemetry** | Monitoring, logging, and observability |

Select which domains to run with the `domains` setting:

- `"default"` -- All 4 domains
- `"repo_manager"` -- Single domain
- `"repo_manager|orchestrator"` -- Multiple domains (regex OR)

---

## Pipeline Stages

```
 Stage                         Mode: default   deploy   cleanup
 ─────────────────────────────────────────────────────────────────
 1. initialization                  Y            Y        Y
 2. setup_environment               Y          (opt)    (opt)
 3. cleanup_<domains>               Y                     Y
 4. cleanup_omnia                   Y                     Y
 5. setup_main                      Y
 6. test_main_installation        (test)       (test)
 7. <domain> deploy                 Y            Y
 8. test_<domain>                 (test)       (test)
 9. summary                         Y            Y        Y
```

`(opt)` = runs only if `ENABLE_SETUP=true` |
`(test)` = runs only if `TEST_MODE=true`

---

## Key Configuration

| Setting | Default | Description |
|---|---|---|
| `pipeline_mode` | `default` | `default`, `deploy`, or `cleanup` |
| `domains` | `default` | Which domains to run (regex pattern) |
| `test_mode` | `false` | Run validation tests after deploy |
| `enable_setup` | `false` | Force setup in deploy/cleanup modes |
| `dry_run` | `false` | Simulate without making changes |
| `verbose` | `false` | Detailed Ansible logging (`-vvv`) |
| `skip_stages` | `""` | Comma-separated stages to skip |

---

## Full Documentation

For detailed instructions on every topic, see [docs/Pipeline_Guide.md](docs/Pipeline_Guide.md):

- OpenBao installation and configuration (Phase 1-3)
- Pipeline modes with examples and scenarios
- Domain selection and combining modes with domains
- Configuration reference (all settings)
- Multi-cluster deployment
- Advanced features (deploy tags, test markers, credential rotation)
- Troubleshooting
- Common commands (`setup_gitlab_project.py` usage)

---

## License

Licensed under the Apache License, Version 2.0. See the Omnia project for
full license text.
