# Omnia CI/CD Pipeline

Automated deployment, cleanup, and validation testing of **Omnia** across
one or more target servers, driven entirely from GitLab CI/CD.

---

## What This Pipeline Does

This pipeline automates the complete lifecycle of Omnia deployments:

- **Setup** — Clones Omnia from GitHub, copies configuration, builds Python venv
- **Cleanup** — Removes previous deployments (optional, can be skipped)
- **Deploy** — Runs Ansible playbooks for 4 domains: repo_manager, image_build_manager, orchestrator, telemetry
- **Test** — Validates each domain with automated test suites
- **Report** — Generates summary and sends email notifications

All of this can be done on **one or many clusters independently** — if cluster1
fails, cluster2 continues unaffected.

---

## Key Features

✅ **Multi-cluster support** — Deploy to 1, 2, 10+ servers independently  
✅ **Flexible modes** — Full cycle, deploy-only, or cleanup-only  
✅ **Domain selection** — Run all domains or specific ones  
✅ **Automated testing** — Validation tests after each domain deploy  
✅ **Configuration-driven** — Single `pipeline_config.yml` file  
✅ **Secure credentials** — Passwords prompted at runtime, never stored  
✅ **Dry-run mode** — Test configuration without making changes  
✅ **Stage control** — Skip specific stages without code changes  

---

## Quick Start

### 1. Fill in `pipeline_config.yml`

```yaml
global:
  clusters: "cluster1"
  omnia:
    repo: "https://github.com/dell/omnia.git"
    branch: "main"
    install_path: "/root/omnia"

cluster1:
  connection:
    target_ip: "10.43.0.100"
    target_user: "root"
  pipeline:
    pipeline_mode: "default"
    domains: "default"
    test_mode: "true"
```

See `pipeline_config.yml` for full documentation.

### 2. Run the setup script

```bash
pip install pyyaml requests

python3 setup_gitlab_project.py --create \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline \
  --config pipeline_config.yml
```

This will:
- Create the GitLab project
- Upload pipeline files
- Upload input templates from Omnia source
- Create all CI/CD variables
- Prompt for SSH passwords (stored securely, never in files)

### 3. Set credential file variables in GitLab

Go to **Settings → CI/CD → Variables** and add File-type variables for
each domain's credentials:

- `CLUSTER1_REPO_MANAGER_CREDS` (File)
- `CLUSTER1_IMAGE_BUILD_CREDS` (File)
- `CLUSTER1_ORCHESTRATOR_CREDS` (File)
- `CLUSTER1_TELEMETRY_CREDS` (File)
- `CLUSTER1_TEST_CREDS` (File, optional)

### 4. Trigger the pipeline

Go to **CI/CD → Pipelines → Run pipeline**.

---

## Pipeline Modes

| Mode | What it does | Use case |
|---|---|---|
| **default** | Cleanup → Setup → Deploy → Test | Initial deployment or full refresh |
| **deploy** | Deploy → Test (skip cleanup) | Incremental updates |
| **cleanup** | Cleanup only | Decommissioning |

Set via `pipeline_mode` in `pipeline_config.yml` or `CLUSTER1_PIPELINE_MODE`
CI/CD variable.

---

## Domains

The pipeline can deploy and test 4 domains independently:

| Domain | Purpose |
|---|---|
| **repo_manager** | Pulp-based package and repository management |
| **image_build_manager** | Container image building and registry |
| **orchestrator** | Kubernetes and container orchestration |
| **telemetry** | Monitoring, logging, and observability |

Run all domains with `domains: "default"`, or select specific ones:
- `domains: "repo_manager"` — Only repo_manager
- `domains: "repo_manager|orchestrator"` — Two domains (regex OR)

---

## Pipeline Stages

The pipeline runs these stages in order (some are conditional):

```
 1. initialization               Load SSH creds, test connectivity
 2. setup_environment            Clone Omnia, copy config, build venv
 3. cleanup_repo_manager         Clean up previous deployment
 4. cleanup_image_build_manager  Clean up previous deployment
 5. cleanup_orchestrator         Clean up previous deployment
 6. cleanup_telemetry            Clean up previous deployment
 7. cleanup_omnia                Destroy venv + data (full reset)
 8. setup_main                  Rebuild venv after cleanup
 9. test_main_installation      Validate Omnia setup
10. repo_manager                 Deploy Pulp repository
11. test_repo_manager            Run repo_manager tests
12. image_build_manager          Deploy image builder
13. test_image_build_manager     Run image builder tests
14. orchestrator                 Deploy Kubernetes
15. test_orchestrator            Run orchestrator tests
16. telemetry                    Deploy monitoring
17. test_telemetry               Run telemetry tests
18. summary                      Generate report + email
```

Which stages run depends on `PIPELINE_MODE`, `DOMAINS`, `TEST_MODE`, and
`SKIP_STAGES`.

---

## Configuration Files

| File | Purpose |
|---|---|
| `pipeline_config.yml` | **Fill this out first** — all pipeline variables |
| `.gitlab-ci.yml` | Parent pipeline (triggers per-cluster jobs) |
| `.gitlab-ci-cluster.yml` | Child pipeline (all stages for one cluster) |
| `setup_gitlab_project.py` | Script to create/update GitLab project |
| `send_email.py` | Email notification helper |

---

## Input Files

The pipeline expects input files in the GitLab repository under
`clusters/<name>/inputs/`:

```
clusters/cluster1/
├── inputs/
│   ├── omnia.env                 Omnia environment config
│   ├── repo_manager/             Domain input files
│   ├── image_build_manager/
│   ├── orchestrator/
│   ├── telemetry/
│   └── test/                     Test configuration files
│       ├── main/
│       ├── repo_manager/
│       ├── image_build_manager/
│       ├── orchestrator/
│       └── telemetry/
└── catalogs/
    └── catalog_rhel.json         Catalog file
```

The setup script automatically uploads templates from the Omnia source tree.
Edit them in GitLab before running the pipeline.

---

## Credentials

**SSH passwords** — Prompted at runtime by the setup script. Stored as
masked CI/CD variables in GitLab. Never written to disk.

**Domain credentials** — Stored as File-type CI/CD variables in GitLab
(e.g. `CLUSTER1_REPO_MANAGER_CREDS`). During the pipeline, credentials
are encrypted with `ansible-vault` on the target server. Never stored
in plaintext in the repository.

**Test credentials** — Optional File-type variable `CLUSTER1_TEST_CREDS`.
Copied to the target for test stages.

---

## Multi-Cluster Deployment

To deploy to multiple servers, add them to `pipeline_config.yml`:

```yaml
global:
  clusters: "cluster1,cluster2,cluster3"

cluster1:
  connection:
    target_ip: "10.43.0.100"
  pipeline:
    pipeline_mode: "default"

cluster2:
  connection:
    target_ip: "10.43.0.200"
  pipeline:
    pipeline_mode: "deploy"

cluster3:
  connection:
    target_ip: "10.43.0.300"
  pipeline:
    pipeline_mode: "cleanup"
```

Each cluster runs as a completely independent pipeline. If one fails, others
continue.

---

## Advanced Features

### Skip Specific Stages

```yaml
pipeline:
  skip_stages: "repo_manager,telemetry"
```

Disables cleanup, deploy, and test for those domains.

### Use Ansible Deploy Tags

```yaml
deploy_tags:
  repo_manager: "deploy"
  orchestrator: "validate"
```

Runs only specific tasks in the playbooks.

### Filter Tests by Pytest Markers

```yaml
test_tags:
  repo_manager: "sanity"
  orchestrator: "sanity+positive"
```

Runs only specific test categories.

### Dry-Run Mode

```yaml
pipeline:
  dry_run: "true"
```

Shows what would happen without executing anything.

### Force Setup in Deploy Mode

```yaml
pipeline:
  pipeline_mode: "deploy"
  enable_setup: "true"
```

Clones latest Omnia and rebuilds venv before deploying.

---

## Documentation

| Document | Content |
|---|---|
| **docs/DETAILED_GUIDE.md** | Complete reference — every stage, variable, command |
| **pipeline_config.yml** | Configuration file with inline documentation |
| `setup_gitlab_project.py --help` | Script command reference |

---

## Troubleshooting

### Pipeline fails at initialization

Check SSH connectivity to the target server. Verify IP, username, password,
and firewall (port 22).

### Deploy stage fails: "Omnia venv not found"

The Python environment hasn't been created. Either:
- Run a `default` mode pipeline first, or
- Set `enable_setup: "true"` to force environment setup

### Deploy stage fails: "CI/CD File Variable not set"

The credential file variable is missing in GitLab. Go to **Settings → CI/CD
→ Variables** and add it as **File** type.

### Deploy stage fails: Ansible playbook error

1. Check input files in `clusters/<name>/inputs/<domain>/`
2. Set `verbose: "true"` for detailed Ansible output
3. Set `dry_run: "true"` to see what would run
4. Check target server meets domain prerequisites

### Tests fail

Test stages are non-fatal. Check deployment succeeded, then:
1. Verify test configuration files are correct
2. If using test tags, verify markers exist in test suite
3. SSH into target and run tests manually to debug

---

## Common Commands

```bash
# Create project from config
python3 setup_gitlab_project.py --create \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline \
  --config pipeline_config.yml

# Update variables after editing config
python3 setup_gitlab_project.py --update \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline \
  --config pipeline_config.yml

# Upload a custom input file
python3 setup_gitlab_project.py --update-file \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline \
  --file /path/to/custom_omnia.env \
  --repo-path clusters/cluster1/inputs/omnia.env

# Validate pipeline YAML
python3 setup_gitlab_project.py --validate \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline
```

---

## Next Steps

1. **Read** `pipeline_config.yml` — understand all configuration options
2. **Fill in** `pipeline_config.yml` with your cluster details
3. **Run** `setup_gitlab_project.py --create --config pipeline_config.yml`
4. **Set** credential file variables in GitLab UI
5. **Edit** input files in GitLab repository
6. **Trigger** the pipeline from GitLab CI/CD

For detailed information on every stage, variable, and command, see
**docs/DETAILED_GUIDE.md**.

---

## License

Licensed under the Apache License, Version 2.0. See the Omnia project for
full license text.
