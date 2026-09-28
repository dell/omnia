# Configuration Reference

Complete reference for all `pipeline_config.yml` settings and CI/CD variables.

---

## pipeline_config.yml Structure

All configuration is in `pipeline_config.yml`. This file is used by `setup_gitlab_project.py` to create CI/CD variables in GitLab.

### Global Settings

```yaml
global:
  clusters: "cluster1,cluster2"
  omnia:
    repo: "https://github.com/dell/omnia.git"
    branch: "main"
    install_path: "/root/omnia"
  vault:
    server_url: "https://10.0.0.50:8200"
    auth_role: "gitlab-role"
    secret_path: "secret/data/omnia"
  email:
    recipients: "admin@example.com,ops@example.com"
    smtp_server: "smtp.example.com"
    smtp_port: 25
```

| Setting | Default | Description |
|---|---|---|
| `global.clusters` | `"cluster1"` | Comma-separated list of cluster names |
| `global.omnia.repo` | `https://github.com/dell/omnia.git` | Omnia Git repository URL |
| `global.omnia.branch` | `main` | Git branch to clone |
| `global.omnia.install_path` | `/root/omnia` | Install path on target server |
| `global.vault.server_url` | `""` | OpenBao server URL (e.g. `https://10.0.0.50:8200`) |
| `global.vault.auth_role` | `gitlab-role` | JWT role name configured in OpenBao |
| `global.vault.secret_path` | `secret/data/omnia` | Base path for domain secrets |
| `global.email.recipients` | `""` | Comma-separated email addresses for notifications |
| `global.email.smtp_server` | `""` | SMTP server hostname |
| `global.email.smtp_port` | `25` | SMTP server port |

---

### Cluster Settings

```yaml
cluster1:
  connection:
    target_ip: "10.43.0.100"
    target_user: "root"
  pipeline:
    pipeline_mode: "default"
    domains: "default"
    enable_setup: "false"
    test_mode: "false"
    dry_run: "false"
    verbose: "false"
    skip_stages: ""
  deploy_tags:
    repo_manager: ""
    image_build_manager: ""
    orchestrator: ""
    telemetry: ""
  test_commands:
    repo_manager: "./run_validation.sh fvt_repo_manager verify"
    image_build_manager: "./run_validation.sh fvt_image_build_manager verify"
    orchestrator: "./run_validation.sh fvt_orchestrator verify"
    telemetry: "./run_validation.sh fvt_telemetry verify"
```

#### Connection Settings

| Setting | Default | Description |
|---|---|---|
| `connection.target_ip` | `""` | IP address of the target server |
| `connection.target_user` | `root` | SSH username |

#### Pipeline Settings

| Setting | Default | Description |
|---|---|---|
| `pipeline.pipeline_mode` | `default` | Pipeline mode: `default`, `deploy`, or `cleanup` |
| `pipeline.domains` | `default` | Which domains to run (regex pattern) |
| `pipeline.enable_setup` | `false` | Force setup in deploy/cleanup modes |
| `pipeline.test_mode` | `false` | Enable test stages after deployment |
| `pipeline.dry_run` | `false` | Simulate without making changes |
| `pipeline.verbose` | `false` | Enable detailed logging (`-vvv`) |
| `pipeline.skip_stages` | `""` | Comma-separated stages to skip |

#### Deploy Tags

Run only specific Ansible tasks using tags:

| Setting | Default | Description |
|---|---|---|
| `deploy_tags.repo_manager` | `""` | Ansible tags for repo_manager playbook |
| `deploy_tags.image_build_manager` | `""` | Ansible tags for image_build_manager playbook |
| `deploy_tags.orchestrator` | `""` | Ansible tags for orchestrator playbook |
| `deploy_tags.telemetry` | `""` | Ansible tags for telemetry playbook |

**Example:**
```yaml
deploy_tags:
  repo_manager: "deploy"
  orchestrator: "validate"
```

#### Test Commands

Override default test commands:

| Setting | Default |
|---|---|
| `test_commands.repo_manager` | `./run_validation.sh fvt_repo_manager verify` |
| `test_commands.image_build_manager` | `./run_validation.sh fvt_image_build_manager verify` |
| `test_commands.orchestrator` | `./run_validation.sh fvt_orchestrator verify` |
| `test_commands.telemetry` | `./run_validation.sh fvt_telemetry verify` |

**Example:**
```yaml
test_commands:
  repo_manager: "./run_validation.sh fvt_repo_manager verify --marker sanity"
  orchestrator: "./run_validation.sh fvt_orchestrator verify --marker sanity+positive"
```

---

## CI/CD Variables

After running `setup_gitlab_project.py --create`, the following CI/CD variables are created in GitLab:

### Global Variables

| Variable | Set by | Description |
|---|---|---|
| `CLUSTERS` | config | Comma-separated cluster names |
| `OMNIA_REPO` | config | Omnia repository URL |
| `OMNIA_BRANCH` | config | Git branch to clone |
| `OMNIA_INSTALL_PATH` | config | Install path on target |
| `BAO_SERVER_URL` | config | OpenBao server URL |
| `BAO_AUTH_ROLE` | config | OpenBao JWT role |
| `BAO_DATA_PATH` | config | OpenBao secret path |
| `EMAIL_RECIPIENTS` | config | Email notification recipients |
| `EMAIL_SENDER` | config | Email sender address |
| `SMTP_SERVER` | config | SMTP server hostname |
| `SMTP_PORT` | config | SMTP server port |

### Per-Cluster Variables

For each cluster, these variables are created with the cluster name prefix (e.g., `CLUSTER1_`, `CLUSTER2_`):

| Variable | Set by | Description |
|---|---|---|
| `<CLUSTER>_TARGET_IP` | manual | Target server IP address |
| `<CLUSTER>_TARGET_USER` | manual | SSH username |
| `<CLUSTER>_TARGET_PASS` | manual | SSH password (masked) |
| `<CLUSTER>_PIPELINE_MODE` | config | Pipeline mode |
| `<CLUSTER>_DOMAINS` | config | Domain selection |
| `<CLUSTER>_ENABLE_SETUP` | config | Force setup |
| `<CLUSTER>_TEST_MODE` | config | Enable tests |
| `<CLUSTER>_DRY_RUN` | config | Dry-run mode |
| `<CLUSTER>_VERBOSE` | config | Verbose logging |
| `<CLUSTER>_REPO_MANAGER_TAGS` | config | Ansible tags |
| `<CLUSTER>_IMAGE_BUILD_MANAGER_TAGS` | config | Ansible tags |
| `<CLUSTER>_ORCHESTRATOR_TAGS` | config | Ansible tags |
| `<CLUSTER>_TELEMETRY_TAGS` | config | Ansible tags |
| `<CLUSTER>_TEST_MAIN_CMD` | config | Test command for main |
| `<CLUSTER>_TEST_REPO_MANAGER_CMD` | config | Test command |
| `<CLUSTER>_TEST_IMAGE_BUILD_MANAGER_CMD` | config | Test command |
| `<CLUSTER>_TEST_ORCHESTRATOR_CMD` | config | Test command |
| `<CLUSTER>_TEST_TELEMETRY_CMD` | config | Test command |
| `<CLUSTER>_SKIP_STAGES` | config | Stages to skip |

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

Each cluster triggers its own independent child pipeline. If one cluster fails, the others continue.

Then update the project:

```bash
python3 setup_gitlab_project.py --update \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline \
    --config pipeline_config.yml
```

The script automatically adds trigger jobs and CI/CD variables for each new cluster.

---

## Advanced Features

### Use Ansible Deploy Tags

Run only specific tasks in the domain playbooks:

```yaml
deploy_tags:
  repo_manager: "deploy"
  orchestrator: "validate"
```

### Override Test Commands

Customize test execution:

```yaml
test_commands:
  repo_manager: "./run_validation.sh fvt_repo_manager verify --marker sanity"
  orchestrator: "./run_validation.sh fvt_orchestrator verify --marker sanity+positive"
```

### Force Setup in Deploy Mode

Clone Omnia and rebuild venv before deploying. Useful when the target server does not have Omnia installed yet:

```yaml
pipeline:
  pipeline_mode: "deploy"
  enable_setup: "true"
```

### Rotating Credentials

Update a credential in OpenBao at any time. The next pipeline run picks up the new value automatically — no GitLab changes needed:

```bash
bao kv put secret/omnia/repo_manager \
    pulp_username="admin" \
    pulp_password="<new-password>" \
    docker_username="<user>" \
    docker_password="<new-password>"
```

---

## Common Commands

### Create a new project from config

```bash
python3 setup_gitlab_project.py --create \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline \
    --config pipeline_config.yml
```

### Update variables and files after editing config

```bash
python3 setup_gitlab_project.py --update \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline \
    --config pipeline_config.yml
```

### Update a specific file in the project

```bash
python3 setup_gitlab_project.py --update-file \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline \
    --file /path/to/omnia.env \
    --repo-path clusters/cluster1/inputs/omnia.env
```

### Upload a local directory to the repo

```bash
python3 setup_gitlab_project.py --upload-dir \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline \
    --dir /path/to/test_configs/ \
    --repo-path clusters/cluster1/inputs/test/orchestrator/
```

### List CI/CD variables

```bash
python3 setup_gitlab_project.py --list-vars \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline
```

### Validate pipeline YAML

```bash
python3 setup_gitlab_project.py --validate \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline
```

### Delete a project

```bash
python3 setup_gitlab_project.py --delete \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline
```

---

## Next Steps

- [Pipeline Modes & Domains](PIPELINE_MODES.md) — Learn deployment strategies
- [Troubleshooting](TROUBLESHOOTING.md) — Solve common issues
