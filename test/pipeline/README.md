# Omnia Pipeline

GitLab CI/CD pipeline for automated Omnia deployment and cleanup on remote clusters.

**Simple by default, scalable when needed:**
- Start with a single cluster (cluster1)
- Add more clusters dynamically using `setup_gitlab_project.py --update --clusters cluster1,cluster2,cluster3`
- Each cluster has its own configuration (CLUSTER1_PIPELINE_MODE, CLUSTER2_PIPELINE_MODE, etc.)
- No global variables, no confusion

Supports three modes — **default** (full cycle), **deploy**, and **cleanup** — controlled
by cluster-level variables. Each cluster runs independently.

## Directory Structure

```
test/pipeline/
├── .gitlab-ci.yml              # Parent pipeline (multi-cluster trigger)
├── .gitlab-ci-cluster.yml      # Child pipeline (per-cluster stages)
├── setup_gitlab_project.py     # GitLab project setup automation script
├── send_email.py               # Email notification script
├── .gitignore                  # Git ignore rules
└── README.md                   # This file

# NOTE: The clusters/ directory is NOT in the repository.
# All cluster configuration is created dynamically in GitLab by setup_gitlab_project.py:
#
# - Cluster connection details (TARGET_IP, TARGET_USER, TARGET_PASS) → CI/CD variables
# - Input files (repo_manager, image_build_manager, orchestrator) → GitLab repository
# - Catalog files → GitLab repository
#
# This approach allows:
#   ✓ Clean repository (no cluster-specific data)
#   ✓ Dynamic cluster management (add/remove clusters without repo changes)
#   ✓ Secure credential storage (passwords in CI/CD variables, not in repo)
#   ✓ Easy multi-cluster deployment
```

## Quick Start

### Single Cluster (Default)

```bash
# Create a new project with a single cluster
python3 setup_gitlab_project.py --create \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline \
  --omnia-src /path/to/omnia \
  --clusters cluster1
```

**Result:**
- `.gitlab-ci.yml` has only cluster1 (simple!)
- 6 cluster-level variables created: `CLUSTER1_PIPELINE_MODE`, `CLUSTER1_DOMAIN`, etc.
- No confusing global variables
- Easy to understand and use

### Multiple Clusters (Dynamic)

```bash
# Create a project with multiple clusters
python3 setup_gitlab_project.py --create \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline \
  --omnia-src /path/to/omnia \
  --clusters cluster1,cluster2,cluster3
```

**Result:**
- `.gitlab-ci.yml` automatically updated with trigger jobs for all clusters
- 18 cluster-level variables created (6 per cluster)
- All trigger jobs dynamically generated
- No manual YAML editing needed

### Add Clusters Later

```bash
# Initially created with 1 cluster
python3 setup_gitlab_project.py --create --clusters cluster1

# Later, add cluster2 and cluster3
python3 setup_gitlab_project.py --update \
  --clusters cluster1,cluster2,cluster3 \
  --update-vars
```

**Result:**
- `.gitlab-ci.yml` automatically updated with new cluster jobs
- New variables created for cluster2 and cluster3
- No manual changes needed
- Seamless scaling

## Pipeline Modes

### Default (`PIPELINE_MODE=default`)

Full cycle — setup, cleanup, then deploy. This is the **default** mode when
`PIPELINE_MODE` is not overridden. Useful for full environment reset and redeployment.

| Stage | Job | Description |
|-------|-----|-------------|
| 1. initialization | `initialization` | Load cluster config, validate SSH |
| 2. setup_environment | `setup_environment` | Clone repo, setup venv, copy catalog |
| 3. cleanup_repo_manager | `cleanup_repo_manager` | `repo_manager.yml` (tags via `CLEANUP_REPO_MANAGER_TAGS`) |
| 4. cleanup_image_build | `cleanup_image_build_manager` | `image_build_manager.yml` (tags via `CLEANUP_IMAGE_BUILD_TAGS`) |
| 5. cleanup_orchestrator | `cleanup_orchestrator` | `cleanup_orchestrator.yml` (tags via `CLEANUP_ORCHESTRATOR_TAGS`) |
| 6. cleanup_omnia | `cleanup_omnia` | `omnia.sh --cleanup --all` |
| 7. test_installation | `test_omnia_installation` | Only if `TEST_MODE=true` |
| 8. repo_manager | `repo_manager` | Copy inputs, encrypt creds, run playbook (tags via `REPO_MANAGER_TAGS`) |
| 9. test_repo_manager | `test_repo_manager` | Only if `TEST_MODE=true` |
| 10. image_build_manager | `image_build_manager` | Copy inputs, encrypt creds, run playbook (tags via `IMAGE_BUILD_MANAGER_TAGS`) |
| 11. test_image_build_manager | `test_image_build_manager` | Only if `TEST_MODE=true` |
| 12. orchestrator | `orchestrator` | Copy inputs, encrypt creds, run playbook (tags via `ORCHESTRATOR_TAGS`) |
| 13. test_orchestrator | `test_orchestrator` | Only if `TEST_MODE=true` |
| 14. summary | `cleanup_summary` + `deploy_summary` | Pipeline reports + email |

### Deploy (`PIPELINE_MODE=deploy`)

Deploy stages only — runs domain playbooks without cleanup first.
Setup is skipped unless `ENABLE_SETUP=true`.

| Stage | Job | Description |
|-------|-----|-------------|
| 1. initialization | `initialization` | Load cluster config, validate SSH |
| 2. setup_environment | `setup_environment` | Only if `ENABLE_SETUP=true` |
| 3. test_installation | `test_omnia_installation` | Only if `TEST_MODE=true` |
| 4. repo_manager | `repo_manager` | Copy inputs, encrypt creds, run playbook (tags via `REPO_MANAGER_TAGS`) |
| 5. test_repo_manager | `test_repo_manager` | Only if `TEST_MODE=true` |
| 6. image_build_manager | `image_build_manager` | Copy inputs, encrypt creds, run playbook (tags via `IMAGE_BUILD_MANAGER_TAGS`) |
| 7. test_image_build_manager | `test_image_build_manager` | Only if `TEST_MODE=true` |
| 8. orchestrator | `orchestrator` | Copy inputs, encrypt creds, run playbook (tags via `ORCHESTRATOR_TAGS`) |
| 9. test_orchestrator | `test_orchestrator` | Only if `TEST_MODE=true` |
| 10. summary | `deploy_summary` | Pipeline report + email notification |

### Cleanup (`PIPELINE_MODE=cleanup`)

Tear down all omnia domain state. Each domain cleanup runs as its own
stage so failures are isolated and visible in the GitLab UI.
Setup is skipped unless `ENABLE_SETUP=true`.

| Stage | Job | Description |
|-------|-----|-------------|
| 1. initialization | `initialization` | Load cluster config, validate SSH |
| 2. setup_environment | `setup_environment` | Only if `ENABLE_SETUP=true` |
| 3. cleanup_repo_manager | `cleanup_repo_manager` | `repo_manager.yml` (tags via `CLEANUP_REPO_MANAGER_TAGS`) |
| 4. cleanup_image_build | `cleanup_image_build_manager` | `image_build_manager.yml` (tags via `CLEANUP_IMAGE_BUILD_TAGS`) |
| 5. cleanup_orchestrator | `cleanup_orchestrator` | `cleanup_orchestrator.yml` (tags via `CLEANUP_ORCHESTRATOR_TAGS`) |
| 6. cleanup_omnia | `cleanup_omnia` | `omnia.sh --cleanup --all` |
| 7. summary | `cleanup_summary` | Pipeline report + email notification |

## Stage Control Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PIPELINE_MODE` | `default` | Pipeline mode: `default`, `deploy`, or `cleanup` |
| `DOMAIN` | `default` | Domain to execute (mandatory) |
| `ENABLE_SETUP` | `false` | Force `setup_environment` in deploy/cleanup modes |
| `TEST_MODE` | `false` | Enable test stages (`test_omnia_installation` + per-domain) |
| `DRY_RUN` | `false` | Log commands without executing ansible playbooks |
| `VERBOSE` | `false` | Run ansible playbooks with `-vvv` instead of `-v` |

### Domain Selection (`DOMAIN` variable)

Select which domain to execute. This is a mandatory variable with `default` as the
default value, which runs all domains.

**Valid values:**

| Value | Description |
|-------|-------------|
| `default` | Run all domains (repo_manager, image_build_manager, orchestrator) |
| `repo_manager` | Run only repo_manager (+ init, summary) |
| `image_build_manager` | Run only image_build_manager (+ init, summary) |
| `orchestrator` | Run only orchestrator (+ init, summary) |

### Test Stages (`TEST_MODE` variable)

When `TEST_MODE=true`, the following test stages are enabled:

- **test_omnia_installation** — Validates omnia setup via the test framework
- **test_repo_manager** — Runs `test/repo_manager/run_validation.sh all verify`
- **test_image_build_manager** — Runs `test/image_build_manager/run_validation.sh all verify`
- **test_orchestrator** — Runs `test/orchestrator/run_validation.sh all verify`

Test stages are `allow_failure: true` — test failures do not block the pipeline.
Per-domain test stages are also gated by the `DOMAIN` selection.

### Per-Stage Ansible Tags

Each domain stage supports an optional ansible `--tags` flag. By default, deploy
stages run without tags (full playbook), and cleanup stages use `--tags cleanup`.

| Variable | Default | Stage |
|----------|---------|-------|
| `REPO_MANAGER_TAGS` | `""` (none) | `repo_manager` deploy |
| `IMAGE_BUILD_MANAGER_TAGS` | `""` (none) | `image_build_manager` deploy |
| `ORCHESTRATOR_TAGS` | `""` (none) | `orchestrator` deploy |
| `CLEANUP_REPO_MANAGER_TAGS` | `cleanup` | `cleanup_repo_manager` |
| `CLEANUP_IMAGE_BUILD_TAGS` | `cleanup` | `cleanup_image_build_manager` |
| `CLEANUP_ORCHESTRATOR_TAGS` | `""` (none) | `cleanup_orchestrator` |

**Examples:**
- Run repo_manager with a specific tag: `REPO_MANAGER_TAGS=install_packages`
- Run cleanup without tags (full playbook): `CLEANUP_REPO_MANAGER_TAGS=""`
- Combine tags: `ORCHESTRATOR_TAGS="network,storage"`

### Optional Setup (`ENABLE_SETUP` variable)

In `deploy` and `cleanup` modes, the `setup_environment` stage is **skipped by default**.
This assumes the omnia venv already exists on the target (from a previous run).

Set `ENABLE_SETUP=true` to force setup in these modes. In `default` mode, setup
always runs regardless of this flag.

### Dry Run (`DRY_RUN` variable)

When `DRY_RUN=true`, all domain stages log what they would execute but skip
the actual `ansible-playbook` commands. Useful for validating pipeline flow
and variable resolution without side effects.

### Verbose Output (`VERBOSE` variable)

When `VERBOSE=true`, ansible playbooks run with `-vvv` instead of the default
`-v`, providing detailed task-level output for debugging.

## Multi-Cluster Configuration

Every control variable supports **per-cluster overrides** using the naming
convention `<CLUSTERNAME>_<VARIABLE>`. If a per-cluster override is not set,
the global value is used automatically via GitLab lazy variable expansion.

### Override Variables

| Global Variable | Per-Cluster Override | Description |
|-----------------|---------------------|-------------|
| `PIPELINE_MODE` | `CLUSTER1_PIPELINE_MODE` | Pipeline mode for this cluster |
| `DOMAIN` | `CLUSTER1_DOMAIN` | Domain selection for this cluster |
| `ENABLE_SETUP` | `CLUSTER1_ENABLE_SETUP` | Force setup for this cluster |
| `TEST_MODE` | `CLUSTER1_TEST_MODE` | Enable tests for this cluster |
| `DRY_RUN` | `CLUSTER1_DRY_RUN` | Dry run for this cluster |
| `VERBOSE` | `CLUSTER1_VERBOSE` | Verbose output for this cluster |

Replace `CLUSTER1` with the uppercase cluster name (e.g. `CLUSTER2_PIPELINE_MODE`,
`CLUSTER3_DOMAIN`).

### How It Works

1. **Global defaults** apply to all clusters: `PIPELINE_MODE=default`, `DOMAIN=default`
2. **Per-cluster overrides** default to the global value: `CLUSTER1_PIPELINE_MODE=$PIPELINE_MODE`
3. When the user sets a per-cluster override (via UI, API, or CI/CD variable), it
   takes precedence over the global default for that cluster only
4. The parent trigger passes the resolved per-cluster value to the child pipeline
5. The child pipeline sees only the final values — no per-cluster logic needed there

### When to Use Global vs Per-Cluster Variables

**Decision Guide:**

| Scenario | Use |
|----------|-----|
| All clusters need the same configuration | **Global variables only** (TEST_MODE, PIPELINE_MODE, etc.) |
| Some clusters need different configuration | **Global + Per-Cluster overrides** (CLUSTER1_TEST_MODE, etc.) |
| Most clusters same, few different | **Global defaults + selective overrides** |

**Quick Rule of Thumb:**

For each variable, ask yourself: **"Do ALL clusters need the SAME value?"**

- **YES** → Set the global variable (e.g., `TEST_MODE=true`)
- **NO** → Set global to default + per-cluster overrides (e.g., `TEST_MODE=false`, then `CLUSTER1_TEST_MODE=true`)

**Examples:**

**Example 1: Same config for all clusters**
```bash
# Set global variables only
PIPELINE_MODE=deploy
DOMAIN=repo_manager
TEST_MODE=false
# All clusters use these values
```

**Example 2: Different config per cluster**
```bash
# Set global defaults
PIPELINE_MODE=deploy
TEST_MODE=false

# Override for specific clusters
CLUSTER1_TEST_MODE=true      # cluster1: tests enabled
CLUSTER2_PIPELINE_MODE=cleanup  # cluster2: cleanup mode
# cluster3: uses global defaults
```

**Example 3: Test one cluster, deploy others**
```bash
# Set global defaults
PIPELINE_MODE=deploy
TEST_MODE=false

# Override for testing
CLUSTER1_TEST_MODE=true
CLUSTER1_DRY_RUN=true
# cluster1: deploy with tests and dry-run (validation)
# cluster2, cluster3: deploy without tests (production)
```

**Key Concept: Lazy Expansion**

Per-cluster variables use GitLab lazy expansion:
```
CLUSTER1_TEST_MODE = $TEST_MODE
```

This means:
- If you set `CLUSTER1_TEST_MODE=true` → cluster1 uses `true` (override)
- If you DON'T set `CLUSTER1_TEST_MODE` → cluster1 uses `TEST_MODE` value (global)

**Best Practices:**

✅ Always set global variables (they serve as defaults)  
✅ Only set per-cluster overrides when needed  
✅ Use global variables for common settings  
✅ Use per-cluster overrides for exceptions  
✅ Keep overrides minimal (easier to maintain)

### Examples

**Same config for all clusters** (default behavior, no per-cluster overrides needed):
```
PIPELINE_MODE=deploy
DOMAIN=repo_manager
CLUSTERS=cluster1,cluster2,cluster3
```
All three clusters run deploy mode with repo_manager only.

**Different modes per cluster:**
```
PIPELINE_MODE=default
CLUSTER1_PIPELINE_MODE=deploy
CLUSTER1_DOMAIN=repo_manager
CLUSTER2_PIPELINE_MODE=cleanup
CLUSTER2_DOMAIN=orchestrator
# cluster3 uses global defaults: PIPELINE_MODE=default, DOMAIN=default
```
- cluster1: deploys repo_manager only
- cluster2: cleans up orchestrator only
- cluster3: full cycle on all domains

**Test one cluster, deploy others:**
```
PIPELINE_MODE=deploy
CLUSTER1_TEST_MODE=true
CLUSTER1_DRY_RUN=true
# cluster2 and cluster3 use global: TEST_MODE=false, DRY_RUN=false
```
- cluster1: deploy with tests and dry-run (validation only)
- cluster2, cluster3: deploy without tests, real execution

### Adding a New Cluster

1. Add the cluster name to the `CLUSTERS` CI/CD variable
2. Create `clusters/<name>/cluster.env` with connection details
3. Add per-cluster override defaults in `.gitlab-ci.yml` variables section:
   ```yaml
   CLUSTER4_PIPELINE_MODE: "$PIPELINE_MODE"
   CLUSTER4_DOMAIN: "$DOMAIN"
   CLUSTER4_ENABLE_SETUP: "$ENABLE_SETUP"
   CLUSTER4_TEST_MODE: "$TEST_MODE"
   CLUSTER4_DRY_RUN: "$DRY_RUN"
   CLUSTER4_VERBOSE: "$VERBOSE"
   ```
4. Add a trigger job (copy an existing `trigger_cluster_*` job and update names)
5. Set `CLUSTER4_TARGET_PASS` as a GitLab CI/CD masked variable

## Venv Gate

Every domain stage (cleanup and deploy) verifies that the omnia venv exists
on the target server before running. The `default:before_script` checks:

- `/opt/omnia/venv` directory exists
- `/opt/omnia/activate-omnia.sh` file exists

If either is missing, the job fails immediately with a clear error message.
The `initialization` and `setup_environment` stages bypass this check since
they are responsible for creating the venv.

## GitLab Project Setup Script

The `setup_gitlab_project.py` script automates GitLab project creation and
configuration. It sources input files directly from the omnia `src/` directory,
eliminating duplicate files.

### Usage

```bash
# Create a new project with pipeline files and input templates
python3 setup_gitlab_project.py --create \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline \
  --omnia-src /path/to/omnia \
  --clusters cluster1,cluster2

# Update an existing project with latest files
python3 setup_gitlab_project.py --update \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline

# Validate pipeline YAML via GitLab CI lint API
python3 setup_gitlab_project.py --validate \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline

# List CI/CD variables (names only, no values)
python3 setup_gitlab_project.py --list-vars \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline
```

#### Script Arguments Explained

| Argument | Required | Description | Example |
|----------|----------|-------------|---------|
| `--create` | Yes (for creation) | Create a new GitLab project | `--create` |
| `--update` | Yes (for update) | Update existing project files | `--update` |
| `--validate` | Yes (for validation) | Validate pipeline YAML syntax | `--validate` |
| `--list-vars` | Yes (for listing) | List all CI/CD variables | `--list-vars` |
| `--gitlab-url` | Yes | GitLab instance URL | `https://gitlab.example.com` |
| `--token` | Yes | GitLab Personal Access Token (prompted if not provided) | `glpat-xxxx` |
| `--project-name` | No | GitLab project name | `omnia-pipeline` (default) |
| `--namespace` | No | GitLab namespace/group | `root` (default) or `my-group` |
| `--omnia-src` | Yes (for `--create`) | Path to omnia repository root or src/ | `/path/to/omnia` |
| `--clusters` | Yes (for `--create`) | Comma-separated cluster names | `cluster1,cluster2,cluster3` |
| `--update-vars` | No | Update CI/CD variables when using `--update` | `--update-vars` |
| `--no-verify-ssl` | No | Disable SSL verification (for self-signed certs) | `--no-verify-ssl` |

#### Interactive Prompts During `--create`

The script will prompt you for:

1. **Cluster Details** (for each cluster):
   ```
   Cluster: cluster1
   Target IP: 10.0.0.1
   Target User: root
   ```

2. **Credential Files** (optional):
   ```
   Upload credential files? (y/n): y
   Path to repo_manager_config_credentials.yml for cluster1: /path/to/creds.yml
   ...
   ```

These prompts allow you to configure cluster-specific connection details that will be stored as CI/CD variables.

### What the Script Does

**Repository Files:**
1. **Copies pipeline files** (`.gitlab-ci.yml`, `.gitlab-ci-cluster.yml`, `send_email.py`)
2. **Copies input templates** from `src/<domain>/input/` for each cluster
3. **Copies catalog** from `src/main/samples/catalog_rhel.json`
4. **Copies omnia.env** template from `src/main/omnia.env`

**CI/CD Variables (NOT in repository):**
5. **Creates cluster connection variables** (per cluster):
   - `CLUSTER<N>_TARGET_IP` - Target cluster IP address
   - `CLUSTER<N>_TARGET_USER` - SSH user (default: root)
   - `CLUSTER<N>_TARGET_PASS` - SSH password (masked, placeholder)
6. **Creates global pipeline control variables**:
   - `PIPELINE_MODE`, `DOMAIN`, `ENABLE_SETUP`, `TEST_MODE`, `DRY_RUN`, `VERBOSE`
   - `REPO_MANAGER_TAGS`, `IMAGE_BUILD_MANAGER_TAGS`, `ORCHESTRATOR_TAGS` (with tag support)
   - `CLEANUP_REPO_MANAGER_TAGS`, `CLEANUP_IMAGE_BUILD_TAGS`, `CLEANUP_ORCHESTRATOR_TAGS`
7. **Creates per-cluster override defaults** (per cluster):
   - `CLUSTER<N>_PIPELINE_MODE=$PIPELINE_MODE`, `CLUSTER<N>_DOMAIN=$DOMAIN`, etc.
   - Uses GitLab lazy expansion to default to global values unless overridden
8. **Optionally uploads credential files** as CI/CD File Variables

#### CI/CD Variables Created by `--create`

For **2 clusters** (cluster1, cluster2):
- **Total: 31-39 variables** (depending on credential file uploads)
  - 1 global (CLUSTERS)
  - 6 cluster connection (3 per cluster)
  - 12 global pipeline control
  - 12 per-cluster overrides (6 per cluster)
  - 0-8 credential files (optional, 4 per cluster)

For **3 clusters** (cluster1, cluster2, cluster3):
- **Total: 40-52 variables** (depending on credential file uploads)
  - 1 global (CLUSTERS)
  - 9 cluster connection (3 per cluster)
  - 12 global pipeline control
  - 18 per-cluster overrides (6 per cluster)
  - 0-12 credential files (optional, 4 per cluster)

**Example for `--create --clusters cluster1,cluster2`:**

```
Configuring CI/CD Variables
============================================================
  created: CLUSTERS = cluster1,cluster2
  created: CLUSTER1_TARGET_IP = 10.0.0.1
  created: CLUSTER1_TARGET_USER = root
  created: CLUSTER1_TARGET_PASS (masked, placeholder — update in GitLab UI)
  created: CLUSTER2_TARGET_IP = 10.0.0.2
  created: CLUSTER2_TARGET_USER = root
  created: CLUSTER2_TARGET_PASS (masked, placeholder — update in GitLab UI)
  created: PIPELINE_MODE = default
  created: DOMAIN = default
  created: ENABLE_SETUP = false
  created: TEST_MODE = false
  created: DRY_RUN = false
  created: VERBOSE = false
  created: REPO_MANAGER_TAGS = 
  created: IMAGE_BUILD_MANAGER_TAGS = 
  created: ORCHESTRATOR_TAGS = 
  created: CLEANUP_REPO_MANAGER_TAGS = cleanup
  created: CLEANUP_IMAGE_BUILD_TAGS = cleanup
  created: CLEANUP_ORCHESTRATOR_TAGS = 
  created: CLUSTER1_PIPELINE_MODE = $PIPELINE_MODE
  created: CLUSTER1_DOMAIN = $DOMAIN
  created: CLUSTER1_ENABLE_SETUP = $ENABLE_SETUP
  created: CLUSTER1_TEST_MODE = $TEST_MODE
  created: CLUSTER1_DRY_RUN = $DRY_RUN
  created: CLUSTER1_VERBOSE = $VERBOSE
  created: CLUSTER2_PIPELINE_MODE = $PIPELINE_MODE
  created: CLUSTER2_DOMAIN = $DOMAIN
  created: CLUSTER2_ENABLE_SETUP = $ENABLE_SETUP
  created: CLUSTER2_TEST_MODE = $TEST_MODE
  created: CLUSTER2_DRY_RUN = $DRY_RUN
  created: CLUSTER2_VERBOSE = $VERBOSE
```

### Input File Sources

| Pipeline Path | Source |
|---------------|--------|
| `clusters/<name>/Inputs/repo_manager/` | `src/repo_manager/input/` |
| `clusters/<name>/Inputs/image_build_manager/` | `src/image_build_manager/input/` |
| `clusters/<name>/Inputs/orchestrator/` | `src/orchestrator/input/` |
| `clusters/<name>/catalogs/catalog_rhel.json` | `src/main/samples/catalog_rhel.json` |
| `clusters/<name>/Inputs/omnia.env` | `src/main/omnia.env` |

## Configuration

### GitLab CI/CD Variables

All variables are configured in **Project > Settings > CI/CD > Variables** — they are NOT defined in the pipeline YAML files.

**Global variables (created by setup script):**

| Variable | Type | Description |
|---|---|---|
| `CLUSTERS` | Variable | Comma-separated list of clusters to run |
| `PIPELINE_MODE` | Variable | Pipeline mode: `default`, `deploy`, or `cleanup` |
| `DOMAIN` | Variable | Domain selection: `default`, `repo_manager`, `image_build_manager`, `orchestrator` |
| `ENABLE_SETUP` | Variable | Force setup stage in deploy/cleanup modes |
| `TEST_MODE` | Variable | Enable test stages |
| `DRY_RUN` | Variable | Log commands without executing |
| `VERBOSE` | Variable | Verbose ansible output |
| `REPO_MANAGER_TAGS` | Variable | Ansible tags for repo_manager deploy |
| `IMAGE_BUILD_MANAGER_TAGS` | Variable | Ansible tags for image_build_manager deploy |
| `ORCHESTRATOR_TAGS` | Variable | Ansible tags for orchestrator deploy |
| `CLEANUP_REPO_MANAGER_TAGS` | Variable | Ansible tags for repo_manager cleanup (default: `cleanup`) |
| `CLEANUP_IMAGE_BUILD_TAGS` | Variable | Ansible tags for image_build_manager cleanup (default: `cleanup`) |
| `CLEANUP_ORCHESTRATOR_TAGS` | Variable | Ansible tags for orchestrator cleanup |

**Cluster connection variables (created by setup script, per cluster):**

| Variable | Type | Description |
|---|---|---|
| `CLUSTER1_TARGET_IP` | Variable | Target cluster IP address |
| `CLUSTER1_TARGET_USER` | Variable | SSH user (default: root) |
| `CLUSTER1_TARGET_PASS` | Variable (masked) | SSH password |
| `CLUSTER1_REPO_MANAGER_CREDS` | **File** | repo_manager_config_credentials.yml |
| `CLUSTER1_IMAGE_BUILD_CREDS` | **File** | image_build_credentials.yml |
| `CLUSTER1_ORCHESTRATOR_CREDS` | **File** | omnia_config_credentials.yml |
| `CLUSTER1_TEST_CREDS` | **File** | test_creds.yml (optional) |

Repeat `CLUSTER2_*` and `CLUSTER3_*` for additional clusters.

**Per-cluster control variable overrides** (optional):

| Variable | Type | Description |
|---|---|---|
| `CLUSTER1_PIPELINE_MODE` | Variable | Override pipeline mode for cluster1 |
| `CLUSTER1_DOMAIN` | Variable | Override domain selection for cluster1 |
| `CLUSTER1_ENABLE_SETUP` | Variable | Override setup flag for cluster1 |
| `CLUSTER1_TEST_MODE` | Variable | Override test mode for cluster1 |
| `CLUSTER1_DRY_RUN` | Variable | Override dry-run flag for cluster1 |
| `CLUSTER1_VERBOSE` | Variable | Override verbose flag for cluster1 |

Repeat for `CLUSTER2_*`, `CLUSTER3_*`, etc. If not set, these default to the global values
via GitLab lazy variable expansion (e.g., `CLUSTER1_PIPELINE_MODE=$PIPELINE_MODE`).

**Optional variables** (defaults in child pipeline if not set):

| Variable | Description | Default |
|---|---|---|
| `SSH_CONNECT_TIMEOUT` | SSH connection timeout in seconds | `30` |
| `OMNIA_REPO` | Git URL for the Omnia repository | `https://github.com/dell/omnia.git` |
| `OMNIA_BRANCH` | Branch to clone | `main` |
| `OMNIA_INSTALL_PATH` | Full path where omnia is installed on target | `/root/omnia` |

**Email notification variables** (optional):

| Variable | Description |
|---|---|
| `EMAIL_RECIPIENTS` | Comma-separated list of recipient emails |
| `EMAIL_SENDER` | From address for emails |
| `SMTP_SERVER` | SMTP relay host |
| `SMTP_PORT` | SMTP relay port (default: 25) |
| `SMTP_USER` | SMTP username (optional) |
| `SMTP_PASSWORD` | SMTP password (optional) |

### Triggering the Pipeline

**From the GitLab UI:**
1. Go to **CI/CD > Pipelines > Run pipeline**
2. Set `CLUSTERS` to the clusters you want to run
3. Set global defaults (`PIPELINE_MODE`, `DOMAIN`, etc.)
4. (Optional) Set per-cluster overrides (`CLUSTER1_PIPELINE_MODE`, etc.)
5. (Optional) Set `TEST_MODE=true` to enable test stages
6. (Optional) Set `DRY_RUN=true` to preview without execution

**From the API:**
```bash
# Full cycle (default mode) on cluster1 and cluster2 — same config
curl --request POST \
  --form "ref=main" \
  --form "variables[CLUSTERS]=cluster1,cluster2" \
  "https://gitlab.example.com/api/v4/projects/<ID>/pipeline"

# Deploy repo_manager on all clusters with verbose output
curl --request POST \
  --form "ref=main" \
  --form "variables[PIPELINE_MODE]=deploy" \
  --form "variables[DOMAIN]=repo_manager" \
  --form "variables[VERBOSE]=true" \
  --form "variables[CLUSTERS]=cluster1,cluster2" \
  "https://gitlab.example.com/api/v4/projects/<ID>/pipeline"

# Per-cluster: deploy repo_manager on cluster1, cleanup orchestrator on cluster2
curl --request POST \
  --form "ref=main" \
  --form "variables[CLUSTERS]=cluster1,cluster2" \
  --form "variables[CLUSTER1_PIPELINE_MODE]=deploy" \
  --form "variables[CLUSTER1_DOMAIN]=repo_manager" \
  --form "variables[CLUSTER2_PIPELINE_MODE]=cleanup" \
  --form "variables[CLUSTER2_DOMAIN]=orchestrator" \
  "https://gitlab.example.com/api/v4/projects/<ID>/pipeline"

# Dry-run one cluster, real deploy on the other
curl --request POST \
  --form "ref=main" \
  --form "variables[PIPELINE_MODE]=deploy" \
  --form "variables[CLUSTERS]=cluster1,cluster2" \
  --form "variables[CLUSTER1_DRY_RUN]=true" \
  "https://gitlab.example.com/api/v4/projects/<ID>/pipeline"

# Deploy with a specific ansible tag on cluster1
curl --request POST \
  --form "ref=main" \
  --form "variables[PIPELINE_MODE]=deploy" \
  --form "variables[CLUSTERS]=cluster1" \
  --form "variables[DOMAIN]=repo_manager" \
  --form "variables[REPO_MANAGER_TAGS]=install_packages" \
  "https://gitlab.example.com/api/v4/projects/<ID>/pipeline"
```

### Cluster Configuration

Each cluster has a `cluster.env` file in `clusters/<name>/`:

```bash
CLUSTER_NAME="cluster1"
TARGET_IP="10.0.0.1"           # Target cluster IP
TARGET_USER="root"             # SSH user
TARGET_PASS="${CLUSTER1_TARGET_PASS}"  # Resolved from GitLab CI/CD variable
```

### Credential Files (CI/CD File Variables)

Credential files are stored as GitLab **CI/CD File Type Variables** — NOT in the
repository. Each cluster has its own set of credential variables, allowing
different credentials per cluster.

**Naming convention:** `<CLUSTER_PREFIX>_<CRED_NAME>`

| CI/CD Variable Name | Target File | Used By Stage |
|---|---|---|
| `CLUSTER1_REPO_MANAGER_CREDS` | `repo_manager_config_credentials.yml` | `repo_manager` |
| `CLUSTER1_IMAGE_BUILD_CREDS` | `image_build_credentials.yml` | `image_build_manager` |
| `CLUSTER1_ORCHESTRATOR_CREDS` | `omnia_config_credentials.yml` | `orchestrator` |
| `CLUSTER1_TEST_CREDS` | `test_creds.yml` | `test_omnia_installation` |

For cluster2 and cluster3, use `CLUSTER2_*` and `CLUSTER3_*` prefixes.

**Setup:**
1. Go to **Settings > CI/CD > Variables**
2. Click **Add variable**
3. Set **Key** to the variable name (e.g., `CLUSTER1_REPO_MANAGER_CREDS`)
4. Set **Type** to **File**
5. Paste the credential file content into the **Value** field
6. Check **Protect variable** (recommended)
7. Do NOT check **Mask variable** (multi-line files cannot be masked)
8. Click **Add variable**
9. Repeat for all credential files and all clusters

**How it works:**

GitLab writes File Type variable content to a temporary file and sets the
variable to the file path. Each domain stage reads the file path from the
corresponding variable and copies it directly to the target server via SCP.
File contents are never printed in the pipeline logs.

**IMPORTANT:** Do not store credential files in the repository. The pipeline
will fail if the required CI/CD File Variable is not set.

## Adding a New Cluster

### Manual Setup

1. **Create cluster directory structure:**
   ```bash
   mkdir -p clusters/<name>/Inputs/{test,repo_manager,image_build_manager,orchestrator}
   mkdir -p clusters/<name>/catalogs
   ```

2. **Create `clusters/<name>/cluster.env`** with connection details:
   ```bash
   CLUSTER_NAME="<name>"
   TARGET_IP="10.0.0.x"
   TARGET_USER="root"
   TARGET_PASS="${<NAME>_TARGET_PASS}"  # Resolved from CI/CD variable
   ```

3. **Create `clusters/<name>/Inputs/omnia.env`** with Omnia environment config

4. **Copy input files** from omnia source:
   - `clusters/<name>/Inputs/repo_manager/` ← from `omnia/src/repo_manager/input/`
   - `clusters/<name>/Inputs/image_build_manager/` ← from `omnia/src/image_build_manager/input/`
   - `clusters/<name>/Inputs/orchestrator/` ← from `omnia/src/orchestrator/input/`
   - `clusters/<name>/catalogs/catalog_rhel.json` ← from `omnia/src/main/samples/`

5. **Add GitLab CI/CD variables** in **Settings > CI/CD > Variables**:
   - `<NAME>_TARGET_PASS` (Type: Variable, masked) — SSH password
   - `<NAME>_REPO_MANAGER_CREDS` (Type: File) — repo_manager_config_credentials.yml
   - `<NAME>_IMAGE_BUILD_CREDS` (Type: File) — image_build_credentials.yml
   - `<NAME>_ORCHESTRATOR_CREDS` (Type: File) — omnia_config_credentials.yml
   - `<NAME>_TEST_CREDS` (Type: File, optional) — test_creds.yml

6. **Add per-cluster override defaults** in `.gitlab-ci.yml` variables section:
   ```yaml
   CLUSTER4_PIPELINE_MODE: "$PIPELINE_MODE"
   CLUSTER4_DOMAIN: "$DOMAIN"
   CLUSTER4_ENABLE_SETUP: "$ENABLE_SETUP"
   CLUSTER4_TEST_MODE: "$TEST_MODE"
   CLUSTER4_DRY_RUN: "$DRY_RUN"
   CLUSTER4_VERBOSE: "$VERBOSE"
   ```

7. **Add a trigger job** in `.gitlab-ci.yml` (copy an existing `trigger_cluster_*` job):
   ```yaml
   trigger_cluster_cluster4:
     stage: trigger
     trigger:
       include:
         - local: .gitlab-ci-cluster.yml
       strategy: depend
     variables:
       CLUSTER: "cluster4"
       PIPELINE_MODE: "$CLUSTER4_PIPELINE_MODE"
       DOMAIN: "$CLUSTER4_DOMAIN"
       ENABLE_SETUP: "$CLUSTER4_ENABLE_SETUP"
       TEST_MODE: "$CLUSTER4_TEST_MODE"
       DRY_RUN: "$CLUSTER4_DRY_RUN"
       VERBOSE: "$CLUSTER4_VERBOSE"
       REPO_MANAGER_TAGS: "$REPO_MANAGER_TAGS"
       IMAGE_BUILD_MANAGER_TAGS: "$IMAGE_BUILD_MANAGER_TAGS"
       ORCHESTRATOR_TAGS: "$ORCHESTRATOR_TAGS"
       CLEANUP_REPO_MANAGER_TAGS: "$CLEANUP_REPO_MANAGER_TAGS"
       CLEANUP_IMAGE_BUILD_TAGS: "$CLEANUP_IMAGE_BUILD_TAGS"
       CLEANUP_ORCHESTRATOR_TAGS: "$CLEANUP_ORCHESTRATOR_TAGS"
     allow_failure: true
     rules:
       - if: '$CLUSTERS =~ /cluster4/'
         when: on_success
   ```

8. **Add the cluster name** to the `CLUSTERS` CI/CD variable (comma-separated list)

### Automated Setup (Recommended)

Use the setup script to automate steps 1-8:

```bash
python3 setup_gitlab_project.py --create \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline \
  --clusters cluster1,cluster2,cluster3,cluster4 \
  --omnia-src /path/to/omnia
```

The script will:
- Create all cluster directories
- Copy input files from omnia source
- Generate cluster.env files
- Create all CI/CD variables (global + per-cluster overrides)
- Prompt for credential file uploads

### Per-Cluster Configuration

Once added, you can configure the new cluster independently:

```bash
# Via GitLab UI: Set per-cluster overrides
CLUSTER4_PIPELINE_MODE=deploy
CLUSTER4_DOMAIN=repo_manager
CLUSTER4_TEST_MODE=true

# Via API:
curl --request POST \
  --form "ref=main" \
  --form "variables[CLUSTERS]=cluster4" \
  --form "variables[CLUSTER4_PIPELINE_MODE]=deploy" \
  --form "variables[CLUSTER4_DOMAIN]=repo_manager" \
  "https://gitlab.example.com/api/v4/projects/<ID>/pipeline"
```

## Target Paths (on remote server)

All paths are derived from `OMNIA_DATA_PATH` (default: `/opt/omnia`) and
`OMNIA_PROJECT_NAME` (default: `project_default`) read from `omnia.env`:

| Pipeline Source | Target Destination |
|---|---|
| `catalogs/catalog_rhel.json` | `<OMNIA_DATA_PATH>/catalog/catalog_rhel.json` |
| `Inputs/repo_manager/*` | `<OMNIA_DATA_PATH>/repo_manager/input/<project>/` |
| `Inputs/image_build_manager/*` | `<OMNIA_DATA_PATH>/image_build_manager/input/<project>/` |
| `Inputs/orchestrator/*` | `<OMNIA_DATA_PATH>/orchestrator/input/<project>/` |

## Credential Encryption

Credential files are automatically encrypted with `ansible-vault` during
the pipeline. For each credential file:
1. A random vault key is generated (`openssl rand -base64 32`)
2. The key is stored alongside the credential file (e.g., `.repo_manager_config_credentials_key`)
3. The credential file is encrypted with `ansible-vault encrypt`
4. The playbook decrypts it at runtime using the vault key

Credential files:
- `repo_manager_config_credentials.yml` -> vault key: `.repo_manager_config_credentials_key`
- `image_build_credentials.yml` -> vault key: `.image_build_credentials_key`
- `omnia_config_credentials.yml` -> vault key: `.omnia_config_credentials_key`

## Email Notifications

The pipeline can send execution reports via email. To enable email notifications:

1. Set the following GitLab CI/CD variables:
   - `EMAIL_RECIPIENTS` - Comma-separated list of recipient emails
   - `EMAIL_SENDER` - From address for emails
   - `SMTP_SERVER` - SMTP relay host
   - `SMTP_PORT` - SMTP relay port (default: 25)
   - `SMTP_USER` - SMTP username (optional, for authenticated relay)
   - `SMTP_PASSWORD` - SMTP password (optional, for authenticated relay)

2. The summary stage runs after the last domain stage (both modes) and
   sends a pipeline summary report

3. Email notifications are non-fatal - pipeline success is not affected if email fails
