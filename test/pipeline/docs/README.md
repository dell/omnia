# Omnia CI/CD Pipeline

Automated deployment, cleanup, and validation testing of Omnia across one or
more target servers, driven entirely from GitLab CI/CD.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
  - [1. Fill in pipeline_config.yml](#1-fill-in-pipeline_configyml)
  - [2. Run the setup script](#2-run-the-setup-script)
  - [3. Set credential file variables in GitLab](#3-set-credential-file-variables-in-gitlab)
  - [4. Edit input files in GitLab](#4-edit-input-files-in-gitlab)
  - [5. Trigger the pipeline](#5-trigger-the-pipeline)
- [Pipeline Modes](#pipeline-modes)
  - [default — Full Cycle](#default--full-cycle)
  - [deploy — Deploy Only](#deploy--deploy-only)
  - [cleanup — Teardown Only](#cleanup--teardown-only)
- [Choosing Which Domains to Run](#choosing-which-domains-to-run)
- [Stage-by-Stage Reference](#stage-by-stage-reference)
  - [initialization](#initialization)
  - [setup_environment](#setup_environment)
  - [Cleanup stages](#cleanup-stages)
  - [setup_main](#setup_main)
  - [Domain deploy stages](#domain-deploy-stages)
  - [Domain test stages](#domain-test-stages)
  - [summary](#summary)
- [Skipping Stages](#skipping-stages)
- [Ansible Deploy Tags](#ansible-deploy-tags)
- [Test Tags (Pytest Markers)](#test-tags-pytest-markers)
- [Multi-Cluster Setup](#multi-cluster-setup)
- [Credentials and Secrets](#credentials-and-secrets)
- [Repository Layout in GitLab](#repository-layout-in-gitlab)
- [CI/CD Variables Reference](#cicd-variables-reference)
- [setup_gitlab_project.py Commands](#setup_gitlab_projectpy-commands)
- [Troubleshooting](#troubleshooting)

---

## How It Works

The pipeline has two layers:

```
.gitlab-ci.yml  (parent)
  |
  |-- trigger_cluster_cluster1  -->  .gitlab-ci-cluster.yml  (child, runs all stages)
  |-- trigger_cluster_cluster2  -->  .gitlab-ci-cluster.yml  (child, independent)
  |-- ...
```

The **parent pipeline** (`.gitlab-ci.yml`) reads the `CLUSTERS` variable
(e.g. `cluster1,cluster2`) and spawns one **child pipeline** per cluster.
Each child runs the full stage sequence independently — if cluster1 fails,
cluster2 keeps going.

Each cluster's child pipeline runs the following stages in order (stages are
skipped or enabled based on `PIPELINE_MODE`, `DOMAINS`, `TEST_MODE`, and
`SKIP_STAGES`):

```
 1. initialization               Always runs. Loads SSH creds, tests connectivity.
 2. setup_environment             Clones Omnia repo on target, copies omnia.env, runs omnia.sh -s.
 3. cleanup_repo_manager          Runs repo_manager.yml --tags cleanup.
 4. cleanup_image_build_manager   Runs image_build_manager.yml --tags cleanup.
 5. cleanup_orchestrator          Runs cleanup_orchestrator.yml --tags cleanup.
 6. cleanup_telemetry             Runs telemetry.yml --tags cleanup.
 7. cleanup_omnia                 Runs omnia.sh --cleanup --all (destroys venv + data).
 8. setup_main                   Rebuilds the venv after cleanup_omnia destroyed it.
 9. test_main_installation       Validates the Omnia installation via run_validation.sh.
10. repo_manager                  Copies inputs + creds, encrypts creds, runs playbook.
11. test_repo_manager             Runs repo_manager validation tests.
12. image_build_manager           Copies inputs + creds, encrypts creds, runs playbook.
13. test_image_build_manager      Runs image_build_manager validation tests.
14. orchestrator                  Copies inputs + creds, encrypts creds, runs playbook.
15. test_orchestrator             Runs orchestrator validation tests.
16. telemetry                     Copies inputs + creds, encrypts creds, runs playbook.
17. test_telemetry                Runs telemetry validation tests.
18. summary                       Generates a report and sends an email notification.
```

Every domain deploy/test stage has a **venv gate** in its `before_script`:
it SSHs into the target, reads `OMNIA_DATA_PATH` from `omnia.env`, and checks
that the venv and `activate-omnia.sh` exist before proceeding. If missing, the
job fails immediately with instructions on how to fix it (run `setup_environment`
or set `ENABLE_SETUP=true`).

---

## Prerequisites

| Requirement | Details |
|---|---|
| GitLab instance | Self-managed or GitLab.com, with CI/CD runners enabled |
| GitLab token | Personal Access Token with `api` scope |
| Python 3.8+ | On the machine where you run `setup_gitlab_project.py` |
| Python packages | `pip install pyyaml requests` |
| Target server(s) | SSH-accessible Linux server(s) where Omnia will be deployed |
| Target SSH user | Usually `root`; needs write access to `OMNIA_INSTALL_PATH` |

---

## Getting Started

### 1. Fill in `pipeline_config.yml`

This file is the single source of truth for all pipeline variables. Open it
and fill in at minimum:

```yaml
global:
  clusters: "cluster1"
  omnia:
    repo: "https://github.com/dell/omnia.git"
    branch: "main"
    install_path: "/root/omnia"

cluster1:
  connection:
    target_ip: "10.43.0.100"          # <-- your target server IP
    target_user: "root"
```

See `pipeline_config.yml` for full documentation on every field.

### 2. Run the setup script

```bash
python3 setup_gitlab_project.py --create \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline \
  --config pipeline_config.yml
```

The script will:

1. Create the GitLab project (or find it if it already exists).
2. Commit pipeline files (`.gitlab-ci.yml`, `.gitlab-ci-cluster.yml`,
   `send_email.py`, `pipeline_config.yml`).
3. Commit domain input templates from the Omnia source tree
   (`src/<domain>/input/` files) into `clusters/<name>/inputs/<domain>/`.
4. Commit test configuration templates (`test_config.yml`,
   `test_run_config.yml`) into `clusters/<name>/inputs/test/<domain>/`.
5. Commit catalog files from `src/main/samples/` into
   `clusters/<name>/catalogs/`.
6. **Prompt for each cluster's SSH password** (entered securely, never
   stored in any file).
7. Create all CI/CD variables in GitLab from the config file.

If variables already exist in GitLab, they are **overwritten** with the
values from the config file.

### 3. Set credential file variables in GitLab

Each domain deploy stage requires an Ansible credentials file. These are
stored as **File-type CI/CD variables** in GitLab:

1. Go to the GitLab project -> **Settings** -> **CI/CD** -> **Variables**
2. For each domain, add a variable:

| Variable Name | Type | Value |
|---|---|---|
| `CLUSTER1_REPO_MANAGER_CREDS` | File | Contents of `repo_manager_config_credentials.yml` |
| `CLUSTER1_IMAGE_BUILD_CREDS` | File | Contents of `image_build_credentials.yml` |
| `CLUSTER1_ORCHESTRATOR_CREDS` | File | Contents of `orchestrator_credentials.yml` |
| `CLUSTER1_TELEMETRY_CREDS` | File | Contents of `telemetry_credentials.yml` |

If you skip this step, the deploy stage for that domain will fail with:
```
ERROR: CI/CD File Variable CLUSTER1_REPO_MANAGER_CREDS not set or file not found
```

Optionally, for test stages:

| Variable Name | Type | Value |
|---|---|---|
| `CLUSTER1_TEST_CREDS` | File | Contents of `test_creds.yml` |

### 4. Edit input files in GitLab

The setup script uploads default input templates. Before running the
pipeline, review and customize them in the GitLab repository:

- `clusters/cluster1/inputs/omnia.env` — Omnia environment settings
  (especially `OMNIA_DATA_PATH`)
- `clusters/cluster1/inputs/repo_manager/` — Repo manager configuration
- `clusters/cluster1/inputs/image_build_manager/` — Image build configuration
- `clusters/cluster1/inputs/orchestrator/` — Orchestrator configuration
- `clusters/cluster1/inputs/telemetry/` — Telemetry configuration
- `clusters/cluster1/catalogs/catalog_rhel.json` — RHEL catalog

### 5. Trigger the pipeline

Go to the GitLab project -> **CI/CD** -> **Pipelines** -> **Run pipeline**.

The pipeline uses the CI/CD variable values set in step 2. To change
behavior (e.g. switch to deploy mode), edit the variables in GitLab UI
before triggering, or update `pipeline_config.yml` and re-run the setup
script with `--update --config pipeline_config.yml`.

---

## Pipeline Modes

Set via `PIPELINE_MODE` (or `pipeline_mode` in the config file).

### `default` — Full Cycle

Runs everything: environment setup, cleanup of previous deployments, venv
rebuild, domain deploys, and tests.

**Stages that execute:**

```
initialization
  -> setup_environment           Clone repo, copy omnia.env, run omnia.sh -s
    -> cleanup_repo_manager      }
    -> cleanup_image_build       } Clean up previous domain state
    -> cleanup_orchestrator      }
    -> cleanup_telemetry         }
    -> cleanup_omnia             Destroy venv + OMNIA_DATA_PATH (only when DOMAINS=default)
      -> setup_main             Rebuild venv via omnia.sh -s
        -> test_main_installation  (if TEST_MODE=true)
        -> repo_manager             }
          -> test_repo_manager      } (if TEST_MODE=true)
        -> image_build_manager      }
          -> test_image_build_manager  }
        -> orchestrator              }
          -> test_orchestrator       }
        -> telemetry                 }
          -> test_telemetry          }
  -> summary
```

When `DOMAINS` is not `default` (e.g. `repo_manager`), `cleanup_omnia` and
`setup_main` are skipped because the venv is needed by other domains.

### `deploy` — Deploy Only

Skips all cleanup stages. Assumes Omnia is already installed on the target
and the venv exists.

**Stages that execute:**

```
initialization
  -> setup_environment           (only if ENABLE_SETUP=true)
  -> repo_manager                }
    -> test_repo_manager         } (if TEST_MODE=true)
  -> image_build_manager         }
    -> test_image_build_manager  }
  -> orchestrator                }
    -> test_orchestrator         }
  -> telemetry                   }
    -> test_telemetry            }
  -> summary
```

If the venv does not exist on the target, the venv gate will fail. Set
`ENABLE_SETUP=true` to force `setup_environment` which clones the repo
and creates the venv.

### `cleanup` — Teardown Only

Runs only the cleanup stages. Does not deploy anything.

**Stages that execute:**

```
initialization
  -> setup_environment           (only if ENABLE_SETUP=true)
  -> cleanup_repo_manager        }
  -> cleanup_image_build         } Clean up selected domains
  -> cleanup_orchestrator        }
  -> cleanup_telemetry           }
  -> cleanup_omnia               (only if DOMAINS=default)
  -> summary
```

Cleanup stages are non-fatal (`allow_failure: true`). If this is a fresh
server with nothing deployed, the cleanup will report "no previous state"
and continue.

---

## Choosing Which Domains to Run

Set via `DOMAINS` (or `domains` in the config file). The value is matched
as a **regex** against domain names.

| Value | Effect |
|---|---|
| `default` | All four domains |
| `repo_manager` | Only repo_manager (cleanup + deploy + test) |
| `image_build_manager` | Only image_build_manager |
| `orchestrator` | Only orchestrator |
| `telemetry` | Only telemetry |
| `repo_manager\|image_build_manager` | Two domains (regex OR) |
| `repo_manager\|orchestrator` | Two domains |
| `repo_manager\|telemetry` | Two domains |
| `image_build_manager\|orchestrator` | Two domains |
| `image_build_manager\|telemetry` | Two domains |
| `orchestrator\|telemetry` | Two domains |

When `DOMAINS` is not `default`, the global `cleanup_omnia` and
`setup_main` stages are skipped (they would destroy the venv that
other domains depend on).

---

## Stage-by-Stage Reference

### `initialization`

- Runs in **all** modes.
- Reads `<CLUSTER>_TARGET_IP`, `<CLUSTER>_TARGET_USER`,
  `<CLUSTER>_TARGET_PASS` from CI/CD variables.
- Tests SSH connectivity to the target.
- Writes `target.env` as a build artifact so later stages can `source` it.
- Records `PIPELINE_TRIGGER_TIME` into `pipeline_time.env`.

If this stage fails, check the target IP, username, password, and firewall.

### `setup_environment`

- Runs in `default` mode, or when `ENABLE_SETUP=true`.
- SSHs into the target and performs:
  1. Installs git if missing.
  2. Removes any existing Omnia directory at `OMNIA_INSTALL_PATH`.
  3. Clones `OMNIA_REPO` (branch `OMNIA_BRANCH`) to `OMNIA_INSTALL_PATH`.
  4. Copies `clusters/<name>/inputs/omnia.env` -> target's
     `OMNIA_INSTALL_PATH/src/main/omnia.env`.
  5. Runs `omnia.sh -s` to create the Python venv and install dependencies.
  6. Copies catalog files to `OMNIA_DATA_PATH/catalog/` (deploy/default mode).

### Cleanup stages

Each domain has its own cleanup stage:

| Stage | What it runs on the target |
|---|---|
| `cleanup_repo_manager` | `ansible-playbook repo_manager.yml --tags cleanup` |
| `cleanup_image_build_manager` | `ansible-playbook image_build_manager.yml --tags cleanup` |
| `cleanup_orchestrator` | `ansible-playbook cleanup_orchestrator.yml --tags cleanup` |
| `cleanup_telemetry` | `ansible-playbook telemetry.yml --tags cleanup` |
| `cleanup_omnia` | `omnia.sh --cleanup --all` (destroys venv, `OMNIA_DATA_PATH`, `/etc/omnia/`) |

All cleanup stages set `allow_failure: true` — if there is nothing to
clean up (first run), the job logs a warning and moves on.

`cleanup_omnia` only runs when `DOMAINS=default` because it destroys the
shared venv.

### `setup_main`

- Runs in `default` mode with `DOMAINS=default` only.
- Re-copies `omnia.env` and runs `omnia.sh -s` to rebuild the venv that
  `cleanup_omnia` just destroyed.
- Re-copies the catalog file to `OMNIA_DATA_PATH/catalog/`.

### Domain deploy stages

Each domain deploy stage (`repo_manager`, `image_build_manager`,
`orchestrator`, `telemetry`) follows the same pattern:

1. **Resolve paths** — Reads `OMNIA_DATA_PATH` and `OMNIA_PROJECT_NAME`
   from the target by activating the Omnia venv.
2. **Copy input files** — SCPs `clusters/<name>/inputs/<domain>/` to the
   target at `OMNIA_DATA_PATH/<domain>/input/OMNIA_PROJECT_NAME/`.
3. **Copy credential file** — Reads the `<CLUSTER>_<DOMAIN>_CREDS` CI/CD
   File Variable and SCPs it to the input directory on the target.
4. **Encrypt credentials** — Uses `ansible-vault encrypt` with an
   auto-generated key file (stored on the target, not in the repo).
5. **Run playbook** — Executes the domain's Ansible playbook. If
   `VERBOSE=true`, runs with `-vvv` instead of `-v`. If deploy tags are
   set, passes `--tags <value>`.

If any step fails, the stage fails. Credentials are encrypted on the target
and never stored in plaintext in the pipeline or the repository.

### Domain test stages

Each domain test stage (`test_repo_manager`, `test_image_build_manager`,
`test_orchestrator`, `test_telemetry`) follows the same pattern:

1. **Copy test config** — SCPs `test_config.yml` and `test_run_config.yml`
   from `clusters/<name>/inputs/test/<domain>/` to the target at
   `OMNIA_INSTALL_PATH/test/<domain>/`.
2. **Copy test credentials** — Reads `<CLUSTER>_TEST_CREDS` File Variable
   and SCPs to the target as `test_creds.yml`.
3. **Install test venv** — Runs `setup_env.sh` on the target to create a
   separate Python venv for tests (distinct from the Omnia deploy venv).
4. **Run tests** — Executes `run_validation.sh all verify`. If test tags
   are set, appends `--marker <value>`.

Test stages are `allow_failure: true` — a test failure does not block
subsequent deploy stages.

### `summary`

- Runs **always** (even if earlier stages fail).
- Generates a text report with pipeline metadata (mode, cluster, domains,
  timestamps, pipeline URL).
- Calls `send_email.py` to send the report to `EMAIL_RECIPIENTS` (if
  configured). Email failure is non-fatal.
- Saves the report as a build artifact at `pipeline_reports/pipeline_summary.txt`.

---

## Skipping Stages

Set `SKIP_STAGES` (or `skip_stages` in the config) to a comma-separated
list of stage identifiers. When a stage's identifier matches, the stage is
set to `when: never` and is completely skipped.

| Identifier | Stages skipped |
|---|---|
| `repo_manager` | `cleanup_repo_manager` + `repo_manager` + `test_repo_manager` |
| `image_build_manager` | `cleanup_image_build_manager` + `image_build_manager` + `test_image_build_manager` |
| `orchestrator` | `cleanup_orchestrator` + `orchestrator` + `test_orchestrator` |
| `telemetry` | `cleanup_telemetry` + `telemetry` + `test_telemetry` |
| `setup_environment` | `setup_environment` only |
| `setup_main` | `setup_main` only |
| `cleanup_omnia` | `cleanup_omnia` only |
| `test_main_installation` | `test_main_installation` only |

Example: `skip_stages: "repo_manager,telemetry"` skips everything related
to repo_manager and telemetry (cleanup, deploy, and test).

This is different from `DOMAINS` — `DOMAINS` selects which domains to
include; `SKIP_STAGES` forcibly removes stages regardless of mode.

---

## Ansible Deploy Tags

Each domain deploy stage accepts an optional Ansible `--tags` value. Set
via `deploy_tags` in the config or the `<CLUSTER>_<DOMAIN>_TAGS` CI/CD
variable.

```yaml
deploy_tags:
  repo_manager: "deploy"       # Only run tasks tagged 'deploy'
  orchestrator: "validate"     # Only run tasks tagged 'validate'
```

When empty (the default), the entire playbook runs without tag filtering.

---

## Test Tags (Pytest Markers)

Each domain test stage accepts an optional pytest marker expression. Set
via `test_tags` in the config or the `<CLUSTER>_TEST_<DOMAIN>_TAGS` CI/CD
variable.

```yaml
test_tags:
  repo_manager: "sanity"             # Run only @pytest.mark.sanity tests
  orchestrator: "sanity+positive"    # Run tests marked both sanity AND positive
  telemetry: "sanity,functional"     # Run tests marked sanity OR functional
```

When empty (the default), all tests run without marker filtering.

The value is passed as `run_validation.sh all verify --marker <value>`.

---

## Multi-Cluster Setup

To deploy to more than one target server:

1. Add cluster names to `pipeline_config.yml`:

```yaml
global:
  clusters: "cluster1,cluster2"

cluster1:
  connection:
    target_ip: "10.43.0.100"
    target_user: "root"
  pipeline:
    pipeline_mode: "default"
    domains: "default"

cluster2:
  connection:
    target_ip: "10.43.0.200"
    target_user: "root"
  pipeline:
    pipeline_mode: "deploy"
    domains: "repo_manager"
```

2. Re-run the setup script:

```bash
python3 setup_gitlab_project.py --create \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline \
  --config pipeline_config.yml
```

The script creates a separate trigger job and set of CI/CD variables for
each cluster. Each cluster runs as a fully independent child pipeline.

---

## Credentials and Secrets

**SSH passwords** — Prompted at runtime by the setup script. Stored as
masked CI/CD variables (`CLUSTER1_TARGET_PASS`) in GitLab. Never written
to any file on disk.

**Domain credentials** (e.g. `repo_manager_config_credentials.yml`) —
Stored as File-type CI/CD variables in GitLab. During the pipeline, the
file is SCPed to the target and encrypted with `ansible-vault` using an
auto-generated key. The plaintext credential file is never stored in the
Git repository.

**Test credentials** (`test_creds.yml`) — Stored as a File-type CI/CD
variable (`CLUSTER1_TEST_CREDS`). Copied to the target for each test
stage. Optional — if not set, tests use defaults.

---

## Repository Layout in GitLab

After setup, the GitLab project contains:

```
.gitlab-ci.yml                           Parent pipeline (triggers per cluster)
.gitlab-ci-cluster.yml                   Child pipeline (all stages)
send_email.py                            Email notification helper
pipeline_config.yml                      Configuration template

clusters/
  cluster1/
    inputs/
      omnia.env                          Omnia environment config
      repo_manager/                      Domain input files
        repo_manager_config.yml
        ...
      image_build_manager/
        image_build_config.yml
        ...
      orchestrator/
        orchestrator_config.yml
        ...
      telemetry/
        telemetry_config.yml
        ...
      test/                              Test configuration files
        main/
          test_config.yml
          test_run_config.yml
        repo_manager/
          test_config.yml
          test_run_config.yml
        image_build_manager/
          test_config.yml
          test_run_config.yml
        orchestrator/
          test_config.yml
          test_run_config.yml
        telemetry/
          test_config.yml
          test_run_config.yml
    catalogs/
      catalog_rhel.json
      ...
```

---

## CI/CD Variables Reference

### Global Variables

| Variable | Default | Description |
|---|---|---|
| `CLUSTERS` | `cluster1` | Comma-separated list of cluster names |
| `OMNIA_REPO` | `https://github.com/dell/omnia.git` | Omnia Git repository URL |
| `OMNIA_BRANCH` | `main` | Branch or tag to checkout |
| `OMNIA_INSTALL_PATH` | `/root/omnia` | Where Omnia is cloned on the target |
| `EMAIL_RECIPIENTS` | _(empty)_ | Comma-separated email addresses for notifications |
| `EMAIL_SENDER` | _(empty)_ | Sender address for email notifications |
| `SMTP_SERVER` | _(empty)_ | SMTP server hostname or IP |
| `SMTP_PORT` | `25` | SMTP port |

### Per-Cluster Variables

Replace `CLUSTER1` with the uppercase cluster name (e.g. `CLUSTER2`).

| Variable | Default | Description |
|---|---|---|
| `CLUSTER1_TARGET_IP` | _(required)_ | SSH target IP or hostname |
| `CLUSTER1_TARGET_USER` | `root` | SSH username |
| `CLUSTER1_TARGET_PASS` | _(required)_ | SSH password (masked in GitLab) |
| `CLUSTER1_PIPELINE_MODE` | `default` | `default`, `deploy`, or `cleanup` |
| `CLUSTER1_DOMAINS` | `default` | Domain selection (regex pattern) |
| `CLUSTER1_ENABLE_SETUP` | `false` | Force setup_environment in deploy/cleanup |
| `CLUSTER1_TEST_MODE` | `false` | Enable test stages |
| `CLUSTER1_DRY_RUN` | `false` | Simulate without executing playbooks |
| `CLUSTER1_VERBOSE` | `false` | Ansible `-vvv` instead of `-v` |
| `CLUSTER1_SKIP_STAGES` | _(empty)_ | Comma-separated stages to skip |
| `CLUSTER1_REPO_MANAGER_TAGS` | _(empty)_ | Ansible `--tags` for repo_manager deploy |
| `CLUSTER1_IMAGE_BUILD_MANAGER_TAGS` | _(empty)_ | Ansible `--tags` for image_build_manager deploy |
| `CLUSTER1_ORCHESTRATOR_TAGS` | _(empty)_ | Ansible `--tags` for orchestrator deploy |
| `CLUSTER1_TELEMETRY_TAGS` | _(empty)_ | Ansible `--tags` for telemetry deploy |
| `CLUSTER1_TEST_REPO_MANAGER_TAGS` | _(empty)_ | Pytest marker for repo_manager tests |
| `CLUSTER1_TEST_IMAGE_BUILD_MANAGER_TAGS` | _(empty)_ | Pytest marker for image_build_manager tests |
| `CLUSTER1_TEST_ORCHESTRATOR_TAGS` | _(empty)_ | Pytest marker for orchestrator tests |
| `CLUSTER1_TEST_TELEMETRY_TAGS` | _(empty)_ | Pytest marker for telemetry tests |

### Per-Cluster File Variables

These must be set as **File** type in GitLab UI (Settings -> CI/CD -> Variables).

| Variable | Description |
|---|---|
| `CLUSTER1_REPO_MANAGER_CREDS` | `repo_manager_config_credentials.yml` contents |
| `CLUSTER1_IMAGE_BUILD_CREDS` | `image_build_credentials.yml` contents |
| `CLUSTER1_ORCHESTRATOR_CREDS` | `orchestrator_credentials.yml` contents |
| `CLUSTER1_TELEMETRY_CREDS` | `telemetry_credentials.yml` contents |
| `CLUSTER1_TEST_CREDS` | `test_creds.yml` contents (optional, shared by all test stages) |

---

## setup_gitlab_project.py Commands

| Command | Purpose |
|---|---|
| `--create` | Create a new GitLab project, upload all files, set CI/CD variables |
| `--update` | Update pipeline files in an existing project |
| `--update --config pipeline_config.yml` | Update pipeline files and refresh CI/CD variables from config |
| `--update --update-vars` | Update pipeline files and reset CI/CD variables to defaults |
| `--validate` | Lint the pipeline YAML via GitLab CI lint API |
| `--list-vars` | List all CI/CD variable names in the project |
| `--update-file --file <path> --repo-path <path>` | Upload a single file to the repository |
| `--upload-dir --dir <path> --repo-path <path>` | Upload an entire directory to the repository |
| `--delete-dir --repo-path <path>` | Delete a directory from the repository |
| `--delete` | Delete the GitLab project (asks for confirmation) |

Common flags: `--gitlab-url`, `--token`, `--project-name`, `--namespace`,
`--no-verify-ssl`.

### Examples

```bash
# Create project from config
python3 setup_gitlab_project.py --create \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline \
  --config pipeline_config.yml

# Update variables after editing the config
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

# Upload an entire directory
python3 setup_gitlab_project.py --upload-dir \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline \
  --dir /path/to/orchestrator_inputs/ \
  --repo-path clusters/cluster1/inputs/orchestrator/

# Validate pipeline YAML
python3 setup_gitlab_project.py --validate \
  --gitlab-url https://gitlab.example.com \
  --token glpat-xxxx \
  --project-name omnia-pipeline
```

---

## Troubleshooting

### initialization fails: "Missing cluster connection variables"

The CI/CD variables `CLUSTER1_TARGET_IP`, `CLUSTER1_TARGET_USER`, and
`CLUSTER1_TARGET_PASS` are not set or are empty.

**Fix:** Re-run the setup script with `--config pipeline_config.yml`, or
set the variables manually in GitLab -> Settings -> CI/CD -> Variables.

### initialization fails: "SSH connection" timeout

The target server is unreachable from the GitLab runner.

**Fix:** Verify the IP is correct, the server is powered on, port 22 is
open, and the GitLab runner has network access to the target.

### Deploy stage fails: "Omnia venv not found"

The venv gate check failed — the Omnia Python environment has not been
created on the target.

**Fix:** Either:
- Run a `default` mode pipeline first (which sets up everything).
- Set `enable_setup: "true"` in the config to force `setup_environment`.

### Deploy stage fails: "CI/CD File Variable ... not set"

The domain credential file variable is missing.

**Fix:** In GitLab -> Settings -> CI/CD -> Variables, add the credential
variable as **File** type (see [Credentials and Secrets](#credentials-and-secrets)).

### Deploy stage fails: Ansible playbook error

**Fix:**
1. Check the input files in `clusters/<name>/inputs/<domain>/` are correct.
2. Set `verbose: "true"` to get `-vvv` Ansible output.
3. Set `dry_run: "true"` to see what commands would run without executing.
4. Check the target server meets the domain's prerequisites.

### Tests fail

Test stages are `allow_failure: true` so they do not block the pipeline.

**Fix:**
1. Check that the deploy stage for that domain succeeded.
2. Verify `test_config.yml` and `test_run_config.yml` are correct.
3. If using test tags, verify the markers exist in the test suite.
4. SSH into the target and run tests manually:
   ```bash
   cd /root/omnia/test/<domain>
   source .venv/bin/activate
   ./run_validation.sh all verify
   ```

### Pipeline does not trigger for a cluster

The `CLUSTERS` variable does not contain the cluster name. The parent
pipeline checks `if: '$CLUSTERS =~ /cluster1/'` to decide whether to
trigger each cluster.

**Fix:** Update `CLUSTERS` to include the missing cluster name.

### How to re-run a single domain without a full cycle

Set `PIPELINE_MODE=deploy`, `DOMAINS=<domain>`, and trigger the pipeline.
Only that domain's deploy stage runs (no cleanup, no other domains).

---

## License

Licensed under the Apache License, Version 2.0. See the Omnia project for
full license text.
