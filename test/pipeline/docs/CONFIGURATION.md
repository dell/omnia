# Configuration Reference

Complete reference for all `pipeline_config.yml` settings and CI/CD variables.

---

## pipeline_config.yml Structure

All configuration is in `pipeline_config.yml`, in the GitLab project.

**Edit the file and commit it: that is all.** The first job of every pipeline (`config`) runs
`pipeline_triggers.py`, which reads the file of the commit being run and passes its values to the
cluster, utils or build stream pipeline of every cluster. No CI/CD variable of the project has to
be changed. For every setting the first non-empty value of these wins:

1. the value in `pipeline_config.yml`;
2. the CI/CD variable of the project with the old name (`<CLUSTER>_PIPELINE_MODE`,
   `<CLUSTER>_OMNIA_BRANCH`, `CLUSTERS`, `UTILS_ENABLE`, ...), so a project that was set up with
   variables keeps working;
3. the default.

An empty value in the file therefore keeps the project variable. The `config` job prints every
value with its source (`<config>`, `<variable>` or `<default>`). Values that rules depend on are
checked (`pipeline_mode`, `utils_mode`, the true/false flags), and a mistake fails that job with
the line of the problem; `$` in a value stays literal.

What stays a CI/CD variable, because it is a secret: the OIM password
(`<CLUSTER>_TARGET_PASS`), the host key (`<CLUSTER>_SSH_KNOWN_HOSTS`, a File variable),
`PIPELINE_API_TOKEN`, the optional `<CLUSTER>_TEST_CREDS` and the SMTP credentials
(`SMTP_USER`, `SMTP_PASSWORD`). The child pipelines inherit them.

`setup_gitlab_project.py` is only needed to create the project, upload the files and store these
secrets.

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
    enable_discovery: "false"
    test_mode: "false"
    dry_run: "false"
    verbose: "false"
    skip_stages: ""
    tolerate_failures: ""
  deploy_tags:
    repo_manager: ""
    image_build_manager: ""
    discovery: ""
    orchestrator: ""
    telemetry: ""
    build_stream: ""
  test_commands:
    repo_manager: "./run_validation.sh fvt_repo_manager verify"
    image_build_manager: "./run_validation.sh fvt_image_build_manager verify"
    discovery: "./run_validation.sh fvt_discovery verify"
    orchestrator: "./run_validation.sh fvt_orchestrator verify"
    telemetry: "./run_validation.sh fvt_telemetry verify"
    build_stream: "./run_validation.sh fvt_build_stream test"
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
| `pipeline.enable_discovery` | `false` | Enable discovery stage after image_build_manager |
| `pipeline.test_mode` | `false` | Enable test stages after deployment |
| `pipeline.dry_run` | `false` | Simulate without making changes |
| `pipeline.verbose` | `false` | Detailed logging: pytest `-v` and ansible `-vvv` (`--ansible-verbosity 3`) in the cluster pipeline |
| `pipeline.tolerate_failures` | `""` | Job names (comma or space separated, for example `cleanup_telemetry,test_cleanup_telemetry`) whose failure is tolerated: the job still runs and is shown as failed in the report and the mail, but it does not block the install and does not fail the pipeline |
| `pipeline.skip_stages` | `""` | Words to skip, comma or space separated, each matched exactly: a domain, a stage name, or `cleanup`, `test_cleanup`, `deploy`, `test`, `nfs_check`, `inputs` (table in [CLUSTER_PIPELINE.md](CLUSTER_PIPELINE.md)) |

#### Deploy Tags

Run only specific Ansible tasks using tags:

| Setting | Default | Description |
|---|---|---|
| `deploy_tags.repo_manager` | `""` | Ansible tags for repo_manager playbook |
| `deploy_tags.image_build_manager` | `""` | Ansible tags for image_build_manager playbook |
| `deploy_tags.orchestrator` | `""` | Ansible tags for orchestrator playbook |
| `deploy_tags.discovery` | `""` | Ansible tags for discovery playbook |
| `deploy_tags.telemetry` | `""` | Ansible tags for telemetry playbook |
| `deploy_tags.build_stream` | `""` | Ansible tags for build_stream playbook |

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
| `test_commands.discovery` | `./run_validation.sh fvt_discovery verify` |
| `test_commands.telemetry` | `./run_validation.sh fvt_telemetry verify` |
| `test_commands.build_stream` | `./run_validation.sh fvt_build_stream test` |

**Example:**
```yaml
test_commands:
  repo_manager: "./run_validation.sh fvt_repo_manager verify --marker sanity"
  orchestrator: "./run_validation.sh fvt_orchestrator verify --marker sanity+positive"
```

---

## CI/CD Variables

`setup_gitlab_project.py` can still store the settings of the file as CI/CD variables. They are the
fallback of step 2 above; the file wins when it has a value:

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

### Variables of the cluster pipeline

Project-level variables that are not per cluster:

| Variable | Default | Description |
|---|---|---|
| `PIPELINE_SSH_KNOWN_HOSTS` | | Host key file for every cluster (instead of `<CLUSTER>_SSH_KNOWN_HOSTS`) |
| `PIPELINE_SSH_SKIP_HOST_KEY` | `false` | `true` accepts an unchecked OIM host key (a warning is printed) |
| `BAO_CA_CERT` | | CA file that verifies the OpenBao TLS certificate |
| `BAO_TLS_SKIP_VERIFY` | `true` | `false` verifies OpenBao with the system certificates |
| `TEST_REPORTS_PATH` | `/automation` | Folder on the OIM with the test reports attached to the email |
| `REPORTS_KEEP_DAYS` | `30` | Reports of earlier pipelines older than this are deleted from that folder by `initialization` |
| `SSH_CONNECT_TIMEOUT` | `30` | SSH connect timeout in seconds |
| `DRY_RUN` | `false` | Per cluster through `<CLUSTER>_DRY_RUN`: print what would run on the OIM |

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
| `<CLUSTER>_ENABLE_DISCOVERY` | config | Enable discovery stage |
| `<CLUSTER>_TEST_MODE` | config | Enable tests |
| `<CLUSTER>_DRY_RUN` | config | Dry-run mode |
| `<CLUSTER>_VERBOSE` | config | Verbose logging |
| `PIPELINE_API_TOKEN` | masked, protected | Project access token (`read_api`, Reporter) used by the summary to read the stage logs for the HTML report |
| `<CLUSTER>_CHECKOUT_MODE` | config | Omnia checkout on the OIM: `update` (default), `recreate` or `keep` |
| `<CLUSTER>_REPO_MANAGER_TAGS` | config | Cluster pipeline: playbook tags (comma list, run with `omnia.sh --run`). Other pipelines: ansible tags |
| `<CLUSTER>_IMAGE_BUILD_MANAGER_TAGS` | config | FVT tags (cluster pipeline) |
| `<CLUSTER>_ORCHESTRATOR_TAGS` | config | FVT tags (cluster pipeline) |
| `<CLUSTER>_DISCOVERY_TAGS` | config | FVT tags (cluster pipeline) |
| `<CLUSTER>_TELEMETRY_TAGS` | config | FVT tags (cluster pipeline) |
| `<CLUSTER>_BUILD_STREAM_TAGS` | config | Ansible tags |
| `<CLUSTER>_TEST_MAIN_CMD` | config | Test command for main |
| `<CLUSTER>_TEST_REPO_MANAGER_CMD` | config | Test command |
| `<CLUSTER>_TEST_IMAGE_BUILD_MANAGER_CMD` | config | Test command |
| `<CLUSTER>_TEST_ORCHESTRATOR_CMD` | config | Test command |
| `<CLUSTER>_TEST_DISCOVERY_CMD` | config | Test command |
| `<CLUSTER>_TEST_TELEMETRY_CMD` | config | Test command |
| `<CLUSTER>_TEST_BUILD_STREAM_CMD` | config | Test command |
| `<CLUSTER>_SKIP_STAGES` | config | Stages to skip |
| `<CLUSTER>_SSH_KNOWN_HOSTS` | `--scan-host-keys` | File variable with the OIM host key line. Required, unless `PIPELINE_SSH_SKIP_HOST_KEY` is `true` |
| `<CLUSTER>_TEST_CREDS` | manual | Optional File variable with the test credentials |

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

### Choose the Deploy Tags

In the cluster pipeline a domain runs its playbook tags in order, in one stage
(`./omnia.sh --run <domain> --tags <tag>`). Give a comma-separated list to run only some of
them; empty means the default list (see [CLUSTER_PIPELINE.md](CLUSTER_PIPELINE.md#domain-stages)):

```yaml
deploy_tags:
  repo_manager: "precheck,prepare"
  orchestrator: "precheck"
```

The build stream and utils pipelines still pass these values as ansible tags.

### Override Test Commands

Customize test execution:

```yaml
test_commands:
  repo_manager: "./run_validation.sh fvt_repo_manager verify --marker sanity"
  orchestrator: "./run_validation.sh fvt_orchestrator verify --marker sanity+positive"
```

### Force Setup in Deploy Mode

Run the install (`setup_main`: `omnia.sh -s`, which creates the Omnia venv) in `deploy` mode. Omnia is always cloned. Useful when the OIM has no Omnia venv yet:

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

### Store the OIM host keys

The jobs need the host key of every OIM. Add `--scan-host-keys` to `--create` or `--update` (with
`--config`): it runs `ssh-keyscan` from this machine and stores `<CLUSTER>_SSH_KNOWN_HOSTS` as a
protected File variable.

```bash
python3 setup_gitlab_project.py --update \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline \
    --config pipeline_config.yml \
    --scan-host-keys
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
    --repo-path clusters/cluster1/inputs/src/main/omnia.env
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
