# Omnia CI/CD Pipeline

Automated deployment, cleanup, and validation testing of Omnia across one or
more target servers, driven entirely from GitLab CI/CD.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [OpenBao Configuration and GitLab Integration](#openbao-configuration-and-gitlab-integration)
   - [Phase 1: Install and Configure OpenBao](#phase-1-install-and-configure-openbao)
   - [Phase 2: Configure Secrets Engine](#phase-2-configure-secrets-engine)
   - [Phase 3: Configure JWT Authentication for GitLab](#phase-3-configure-jwt-authentication-for-gitlab)
4. [Getting Started](#getting-started)
   - [Step 1: Fill in pipeline_config.yml](#step-1-fill-in-pipeline_configyml)
   - [Step 2: Run the setup script](#step-2-run-the-setup-script)
   - [Step 3: Edit input files in GitLab](#step-3-edit-input-files-in-gitlab)
   - [Step 4: Trigger the pipeline](#step-4-trigger-the-pipeline)
5. [Pipeline Modes](#pipeline-modes)
6. [Domains](#domains)
7. [Pipeline Stages](#pipeline-stages)
8. [Configuration Reference](#configuration-reference)
9. [Multi-Cluster Deployment](#multi-cluster-deployment)
10. [Advanced Features](#advanced-features)
11. [Troubleshooting](#troubleshooting)
12. [Common Commands](#common-commands)

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

## OpenBao Configuration and GitLab Integration

The pipeline fetches domain credentials from OpenBao using JWT authentication.
Each pipeline job gets a short-lived JWT token from GitLab, authenticates with
OpenBao, and reads the credentials it needs. No static secrets are stored in
GitLab.

**Complete this section before proceeding to [Getting Started](#getting-started).**

### Phase 1: Install and Configure OpenBao

#### 1.1 Download and Install

```bash
curl -LO https://github.com/openbao/openbao/releases/download/v2.1.0/bao_2.1.0_linux_amd64.rpm
sudo yum localinstall bao_2.1.0_linux_amd64.rpm
```

#### 1.2 Verify Installation

```bash
which bao
bao version

# Check config and TLS files
cat /etc/openbao/openbao.hcl
ls -la /opt/openbao/tls/
```

#### 1.3 Configure OpenBao

```bash
sudo vi /etc/openbao/openbao.hcl
```

Set the following content:

```hcl
ui = true

storage "file" {
  path = "/opt/openbao/data"
}

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/opt/openbao/tls/tls.crt"
  tls_key_file  = "/opt/openbao/tls/tls.key"
}

api_addr = "https://<YOUR_SERVER_IP>:8200"
```

> Replace `<YOUR_SERVER_IP>` with the IP address of the OpenBao server.

#### 1.4 Open Firewall Port

```bash
sudo firewall-cmd --permanent --add-port=8200/tcp
sudo firewall-cmd --reload
```

#### 1.5 Start OpenBao Service

```bash
sudo systemctl enable openbao
sudo systemctl start openbao
sudo systemctl status openbao
```

#### 1.6 Set Environment Variables

```bash
export BAO_ADDR='https://127.0.0.1:8200'
export BAO_SKIP_VERIFY=true

# Make persistent across sessions
echo 'export BAO_ADDR="https://127.0.0.1:8200"' >> ~/.bashrc
echo 'export BAO_SKIP_VERIFY=true' >> ~/.bashrc
source ~/.bashrc
```

#### 1.7 Initialize and Unseal

**Initialize:**

```bash
bao operator init
```

> **SAVE the 5 unseal keys and root token securely!**
> These are required to unseal the vault after every restart.

**Unseal (3 of 5 keys required):**

```bash
bao operator unseal    # Enter Unseal Key 1
bao operator unseal    # Enter Unseal Key 2
bao operator unseal    # Enter Unseal Key 3
```

**Verify status:**

```bash
bao status
```

Expected:

```
Initialized     true
Sealed          false
```

**Login:**

```bash
bao login
# Enter root token when prompted
```

### Phase 2: Configure Secrets Engine

#### 2.1 Enable KV v2 Secrets Engine

```bash
bao secrets enable -path=secret kv-v2
```

#### 2.2 Store Domain Credentials

```bash
# Repo Manager credentials
bao kv put secret/omnia/repo_manager \
    pulp_username="admin" \
    pulp_password="<YourPulpPassword>" \
    docker_username="<yourdockeruser>" \
    docker_password="<YourDockerPassword>"

# Image Build Manager credentials
bao kv put secret/omnia/image_build_manager \
    aarch64_ssh_password="<YourPassword>" \
    s3_access_id="<YourS3AccessID>" \
    s3_secret_key="<YourS3SecretKey>"

# Orchestrator credentials
bao kv put secret/omnia/orchestrator \
    provision_password="<ProvPass>" \
    bmc_username="root" \
    bmc_password="<BmcPass>" \
    slurm_db_password="<SlurmPass>" \
    openldap_db_username="admin" \
    openldap_db_password="<LdapPass>" \
    csi_username="" \
    csi_password=""

# Telemetry credentials
bao kv put secret/omnia/telemetry \
    bmc_username="admin" \
    bmc_password="<BmcPassword>" \
    mysqldb_user="admin" \
    mysqldb_password="<MysqlPwd>" \
    mysqldb_root_password="<MysqlRootPwd>" \
    csi_username="admin" \
    csi_password="<CsiPassword>" \
    ldms_sampler_password="<LdmsPwd>" \
    ufm_username="admin" \
    ufm_password="<UfmPassword>" \
    vast_username="admin" \
    vast_password="<VastPassword>"
```

#### 2.3 Verify Secrets

```bash
bao kv list secret/omnia/
bao kv get secret/omnia/repo_manager
```

### Phase 3: Configure JWT Authentication for GitLab

#### 3.1 Extract GitLab SSL Certificate

If GitLab uses a self-signed or internal CA certificate:

```bash
echo | openssl s_client -connect <GITLAB_IP>:443 2>/dev/null | \
    openssl x509 -out /tmp/gitlab.crt
```

#### 3.2 Enable JWT Auth Method

```bash
bao auth enable jwt
```

#### 3.3 Configure JWT with GitLab OIDC Discovery

```bash
bao write auth/jwt/config \
    oidc_discovery_url="https://<GITLAB_URL>" \
    bound_issuer="https://<GITLAB_URL>" \
    oidc_discovery_ca_pem=@/tmp/gitlab.crt
```

**Verify:**

```bash
bao read auth/jwt/config
```

#### 3.4 Create Policy

```bash
cat <<EOF > gitlab-policy.hcl
path "secret/data/omnia/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/omnia/*" {
  capabilities = ["read", "list"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}
EOF

bao policy write gitlab-policy gitlab-policy.hcl
```

#### 3.5 Create JWT Role for GitLab

```bash
bao write auth/jwt/role/gitlab-role \
    role_type="jwt" \
    policies="gitlab-policy" \
    token_explicit_max_ttl=3600 \
    user_claim="user_email" \
    bound_audiences="https://<OPENBAO_SERVER_IP>:8200"
```

**Verify:**

```bash
bao read auth/jwt/role/gitlab-role
```

#### 3.6 Set GitLab CI/CD Variables

Go to your GitLab project > **Settings** > **CI/CD** > **Variables** and add:

| Variable | Value | Type |
|---|---|---|
| `VAULT_SERVER_URL` | `https://<OPENBAO_IP>:8200` | Variable |
| `VAULT_AUTH_ROLE` | `gitlab-role` | Variable |
| `VAULT_SECRET_PATH` | `secret/data/omnia` | Variable |

These are also set automatically when using `pipeline_config.yml` with the
setup script.

---

## Getting Started

> **Note:** Complete the [OpenBao Configuration](#openbao-configuration-and-gitlab-integration)
> section above before proceeding.

### Step 1: Fill in pipeline_config.yml

Open `pipeline_config.yml` and fill in your cluster connection details and
pipeline settings:

```yaml
global:
  clusters: "cluster1"
  omnia:
    repo: "https://github.com/dell/omnia.git"
    branch: "main"
    install_path: "/root/omnia"
  vault:
    server_url: "https://<OPENBAO_IP>:8200"
    auth_role: "gitlab-role"
    secret_path: "secret/data/omnia"

cluster1:
  connection:
    target_ip: "10.43.0.100"
    target_user: "root"
  pipeline:
    pipeline_mode: "default"
    domains: "default"
    test_mode: "true"
```

See `pipeline_config.yml` for full documentation of every option.

### Step 2: Run the setup script

```bash
pip install pyyaml requests

python3 setup_gitlab_project.py --create \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline \
    --config pipeline_config.yml
```

The script will:
- Create the GitLab project
- Upload all pipeline files (`.gitlab-ci.yml`, `.gitlab-ci-cluster.yml`, etc.)
- Upload input file templates from the Omnia source tree
- Create all CI/CD variables from your config
- Prompt for SSH passwords (stored as masked CI/CD variables, never in files)

### Step 3: Edit input files in GitLab

After the project is created, go to the GitLab repository and edit the input
files under `clusters/cluster1/inputs/` to match your environment:

- `omnia.env` -- Omnia environment settings
- `repo_manager/` -- Pulp repository configuration
- `orchestrator/` -- Kubernetes/orchestration configuration
- `image_build_manager/` -- Image build settings
- `telemetry/` -- Monitoring and observability settings

### Step 4: Trigger the pipeline

Go to **CI/CD > Pipelines > Run pipeline** in your GitLab project.

---

## Pipeline Modes

The pipeline supports three execution modes that control which stages run.
Set the mode via `pipeline_mode` in `pipeline_config.yml` or the
`CLUSTER1_PIPELINE_MODE` CI/CD variable.

### `default` -- Full Cycle

Runs the complete lifecycle: setup the environment, clean up any previous
deployment, rebuild the venv, deploy all selected domains, run tests, and
generate a summary.

**Use when:** First-time deployment, or when you want a clean full refresh.

**Flow:**
```
initialization > setup_environment > cleanup_<domains> > cleanup_omnia >
setup_main > test_main > deploy_<domains> > test_<domains> > summary
```

**Example:**
```yaml
pipeline:
  pipeline_mode: "default"
  domains: "default"       # all 4 domains
  test_mode: "true"        # run validation tests after deploy
```

### `deploy` -- Deploy Only

Skips cleanup and setup. Directly copies input files, fetches credentials
from OpenBao, and runs the domain playbooks. Requires the Omnia venv to
already exist on the target (from a previous `default` run or manual setup).

**Use when:** Pushing incremental updates, re-running a specific domain
after changing input files, or redeploying after a credential rotation.

**Flow:**
```
initialization > deploy_<domains> > test_<domains> > summary
```

**Example:**
```yaml
pipeline:
  pipeline_mode: "deploy"
  domains: "repo_manager"    # redeploy only repo_manager
  test_mode: "false"
```

If the target does not have Omnia installed yet, add `enable_setup: "true"`
to force the setup_environment stage:

```yaml
pipeline:
  pipeline_mode: "deploy"
  enable_setup: "true"
  domains: "orchestrator"
```

### `cleanup` -- Tear Down

Runs domain-specific cleanup playbooks (`--tags cleanup`) and optionally
runs `omnia.sh --cleanup --all` to destroy the venv and all data.

**Use when:** Decommissioning a server, resetting the environment before
a fresh deployment, or cleaning up specific domains.

**Flow:**
```
initialization > setup_environment (if enable_setup) > cleanup_<domains> >
cleanup_omnia (only if domains=default) > summary
```

**Example -- clean up everything:**
```yaml
pipeline:
  pipeline_mode: "cleanup"
  domains: "default"          # cleanup all domains + omnia venv
```

**Example -- clean up only orchestrator:**
```yaml
pipeline:
  pipeline_mode: "cleanup"
  domains: "orchestrator"     # only cleanup orchestrator, keep others intact
```

---

## Domains

The pipeline manages 4 independent domains. Each domain has its own cleanup,
deploy, and test stages. You can run all domains or select specific ones.

| Domain | Purpose | Credential file |
|---|---|---|
| **repo_manager** | Pulp-based package and repository management | `repo_manager_config_credentials.yml` |
| **image_build_manager** | Container image building and registry | `image_build_credentials.yml` |
| **orchestrator** | Kubernetes and container orchestration | `orchestrator_credentials.yml` |
| **telemetry** | Monitoring, logging, and observability | `telemetry_credentials.yml` |

### Domain Selection

Set via `domains` in `pipeline_config.yml` or the `CLUSTER1_DOMAINS` CI/CD
variable. The value is treated as a **regex pattern** matched against each
domain name.

| Setting | Domains that run | When to use |
|---|---|---|
| `"default"` | All 4 domains | Full deployment |
| `"repo_manager"` | repo_manager only | Initial repo setup or repo update |
| `"orchestrator"` | orchestrator only | Deploy/redeploy Kubernetes |
| `"telemetry"` | telemetry only | Deploy monitoring stack |
| `"image_build_manager"` | image_build_manager only | Deploy image builder |
| `"repo_manager\|orchestrator"` | repo_manager + orchestrator | Deploy two domains together |
| `"repo_manager\|image_build_manager\|telemetry"` | Three domains (skip orchestrator) | Everything except orchestrator |

### Combining Modes and Domains

These two settings work together. Here are common real-world scenarios:

**Scenario 1: First-time full deployment with tests**
```yaml
pipeline:
  pipeline_mode: "default"
  domains: "default"
  test_mode: "true"
```

**Scenario 2: Redeploy only repo_manager after changing Pulp credentials**
```yaml
pipeline:
  pipeline_mode: "deploy"
  domains: "repo_manager"
  test_mode: "false"
```

**Scenario 3: Clean up orchestrator, then redeploy it fresh**
```yaml
# Run 1: cleanup
pipeline:
  pipeline_mode: "cleanup"
  domains: "orchestrator"

# Run 2: deploy
pipeline:
  pipeline_mode: "deploy"
  domains: "orchestrator"
  enable_setup: "true"
```

**Scenario 4: Deploy repo_manager and telemetry together, skip others**
```yaml
pipeline:
  pipeline_mode: "deploy"
  domains: "repo_manager|telemetry"
  test_mode: "true"
```

**Scenario 5: Full cleanup of everything on the target**
```yaml
pipeline:
  pipeline_mode: "cleanup"
  domains: "default"
```
This runs all domain cleanups AND `omnia.sh --cleanup --all` which destroys
the venv, `$OMNIA_DATA_PATH`, and `/etc/omnia/`.

**Scenario 6: Dry-run to preview what would happen**
```yaml
pipeline:
  pipeline_mode: "default"
  domains: "default"
  dry_run: "true"
```
Logs all commands without executing any Ansible playbooks.

### Skipping Specific Domains

Use `skip_stages` to exclude domains without changing the `domains` setting.
This is useful when `domains: "default"` but you want to temporarily skip
one domain:

```yaml
pipeline:
  pipeline_mode: "default"
  domains: "default"
  skip_stages: "telemetry"         # skip telemetry cleanup + deploy + test
```

You can skip multiple domains:
```yaml
skip_stages: "image_build_manager,telemetry"
```

Valid values for `skip_stages`:
- `repo_manager`, `image_build_manager`, `orchestrator`, `telemetry` --
  skips cleanup + deploy + test for that domain
- `setup_environment`, `setup_main`, `cleanup_omnia` --
  skips that specific stage

---

## Pipeline Stages

The pipeline runs these stages in order. Which stages actually execute depends
on `PIPELINE_MODE`, `DOMAINS`, `TEST_MODE`, and `SKIP_STAGES`.

```
 Stage                         Mode: default   deploy   cleanup
 ─────────────────────────────────────────────────────────────────
 1. initialization                  Y            Y        Y
 2. setup_environment               Y          (opt)    (opt)
 3. cleanup_repo_manager            Y                     Y
 4. cleanup_image_build_manager     Y                     Y
 5. cleanup_orchestrator            Y                     Y
 6. cleanup_telemetry               Y                     Y
 7. cleanup_omnia                   Y                     Y
 8. setup_main                      Y
 9. test_main_installation        (test)       (test)
10. repo_manager                    Y            Y
11. test_repo_manager             (test)       (test)
12. image_build_manager             Y            Y
13. test_image_build_manager      (test)       (test)
14. orchestrator                    Y            Y
15. test_orchestrator             (test)       (test)
16. telemetry                       Y            Y
17. test_telemetry                (test)       (test)
18. summary                         Y            Y        Y
```

`(opt)` = runs only if `ENABLE_SETUP=true`
`(test)` = runs only if `TEST_MODE=true`

**What each stage does:**

| Stage | Description |
|---|---|
| **initialization** | Loads cluster config from CI/CD variables, validates SSH connectivity, checks OpenBao reachability, writes `target.env` for downstream stages |
| **setup_environment** | Clones Omnia repo on target, copies `omnia.env`, runs `omnia.sh -s` to build venv, copies catalog file |
| **cleanup_\<domain\>** | Runs the domain's cleanup playbook (`--tags cleanup`). Non-fatal -- first run has nothing to clean |
| **cleanup_omnia** | Runs `omnia.sh --cleanup --all` to destroy venv and data. Only runs when `DOMAINS=default` |
| **setup_main** | Rebuilds the venv after `cleanup_omnia` destroyed it. Re-copies `omnia.env` and catalog |
| **test_main_installation** | Installs the test venv and runs `run_validation.sh all verify` |
| **\<domain\>** | Copies input files to target, fetches credentials from OpenBao (JWT auth), encrypts with ansible-vault, runs the domain playbook |
| **test_\<domain\>** | Copies test config to target, installs test venv, runs domain validation tests. Non-fatal |
| **summary** | Generates a pipeline report and sends email notification |

---

## Configuration Reference

All configuration is in `pipeline_config.yml`. Key sections:

### Global Settings

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

### Cluster Settings

| Setting | Default | Description |
|---|---|---|
| `connection.target_ip` | `""` | IP address of the target server |
| `connection.target_user` | `root` | SSH username |
| `pipeline.pipeline_mode` | `default` | Pipeline mode: `default`, `deploy`, or `cleanup` |
| `pipeline.domains` | `default` | Which domains to run (regex pattern) |
| `pipeline.enable_setup` | `false` | Force setup in deploy/cleanup modes |
| `pipeline.test_mode` | `false` | Enable test stages after deployment |
| `pipeline.dry_run` | `false` | Simulate without making changes |
| `pipeline.verbose` | `false` | Enable detailed logging (`-vvv`) |
| `pipeline.skip_stages` | `""` | Comma-separated stages to skip |

### Deploy Tags

| Setting | Default | Description |
|---|---|---|
| `deploy_tags.repo_manager` | `""` | Ansible tags for repo_manager playbook |
| `deploy_tags.image_build_manager` | `""` | Ansible tags for image_build_manager playbook |
| `deploy_tags.orchestrator` | `""` | Ansible tags for orchestrator playbook |
| `deploy_tags.telemetry` | `""` | Ansible tags for telemetry playbook |

### Test Commands

| Setting | Default |
|---|---|
| `test_commands.repo_manager` | `./run_validation.sh fvt_repo_manager verify` |
| `test_commands.image_build_manager` | `./run_validation.sh fvt_image_build_manager verify` |
| `test_commands.orchestrator` | `./run_validation.sh fvt_orchestrator verify` |
| `test_commands.telemetry` | `./run_validation.sh fvt_telemetry verify` |

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

Each cluster triggers its own independent child pipeline. If one cluster
fails, the others continue.

Then update the project:

```bash
python3 setup_gitlab_project.py --update \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline \
    --config pipeline_config.yml
```

The script automatically adds trigger jobs and CI/CD variables for each
new cluster.

---

## Advanced Features

### Use Ansible Deploy Tags

```yaml
deploy_tags:
  repo_manager: "deploy"
  orchestrator: "validate"
```

Runs only specific tasks in the domain playbooks.

### Override Test Commands

```yaml
test_commands:
  repo_manager: "./run_validation.sh fvt_repo_manager verify --marker sanity"
  orchestrator: "./run_validation.sh fvt_orchestrator verify --marker sanity+positive"
```

### Force Setup in Deploy Mode

```yaml
pipeline:
  pipeline_mode: "deploy"
  enable_setup: "true"
```

Clones Omnia and rebuilds venv before deploying. Useful when the target
server does not have Omnia installed yet.

### Rotating Credentials

Update a credential in OpenBao at any time. The next pipeline run picks up
the new value automatically -- no GitLab changes needed:

```bash
bao kv put secret/omnia/repo_manager \
    pulp_username="admin" \
    pulp_password="<new-password>" \
    docker_username="<user>" \
    docker_password="<new-password>"
```

---

## Troubleshooting

### Pipeline fails at initialization

- Check SSH connectivity to the target server
- Verify IP address, username, password, and firewall (port 22)
- Ensure `CLUSTER1_TARGET_IP`, `CLUSTER1_TARGET_USER`, and
  `CLUSTER1_TARGET_PASS` are set in GitLab CI/CD variables

### "OpenBao server is NOT reachable"

The pipeline validates OpenBao connectivity during initialization:
1. Verify `VAULT_SERVER_URL` is correct (e.g. `https://10.0.0.50:8200`)
2. Check if OpenBao is running: `sudo systemctl status openbao`
3. Verify network connectivity from the GitLab Runner to the OpenBao host
4. Check firewall rules: `firewall-cmd --list-ports` (must include 8200/tcp)

### "OpenBao authentication failed"

JWT validation failed:
1. Verify `oidc_discovery_url` matches your GitLab instance URL
2. Verify `bound_audiences` in the role matches the OpenBao server URL
3. If GitLab uses a self-signed certificate, verify `oidc_discovery_ca_pem`
   was set (see Phase 3.3)
4. Confirm GitLab version is 15.7+ (required for `id_tokens`)

### "Failed to fetch secret"

1. Verify the secret exists: `bao kv get secret/omnia/<domain>`
2. Check the policy path includes `/data/` for KV v2: `secret/data/omnia/*`
3. Verify `VAULT_SECRET_PATH` is set to `secret/data/omnia`

### "Omnia venv not found"

The Python environment has not been created on the target. Either:
- Run a `default` mode pipeline first (includes full setup), or
- Set `enable_setup: "true"` to force environment setup

### "CI/CD File Variable not set"

Test credential file variable is missing. Go to **Settings > CI/CD >
Variables** and add `CLUSTER1_TEST_CREDS` as a **File** type variable.

### Deploy fails with Ansible errors

1. Check input files in `clusters/<name>/inputs/<domain>/`
2. Set `verbose: "true"` for detailed Ansible output (`-vvv`)
3. Set `dry_run: "true"` to see what would run without executing
4. SSH into target and run the playbook manually to debug

---

## Common Commands

```bash
# Create a new project from config
python3 setup_gitlab_project.py --create \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline \
    --config pipeline_config.yml

# Update variables and files after editing config
python3 setup_gitlab_project.py --update \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline \
    --config pipeline_config.yml

# Update a specific file in the project
python3 setup_gitlab_project.py --update-file \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline \
    --file /path/to/omnia.env \
    --repo-path clusters/cluster1/inputs/omnia.env

# Upload a local directory to the repo
python3 setup_gitlab_project.py --upload-dir \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline \
    --dir /path/to/test_configs/ \
    --repo-path clusters/cluster1/inputs/test/orchestrator/

# List CI/CD variables
python3 setup_gitlab_project.py --list-vars \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline

# Validate pipeline YAML
python3 setup_gitlab_project.py --validate \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline

# Delete a project
python3 setup_gitlab_project.py --delete \
    --gitlab-url https://gitlab.example.com \
    --token glpat-xxxx \
    --project-name omnia-pipeline
```

---

## License

Licensed under the Apache License, Version 2.0. See the Omnia project for
full license text.
