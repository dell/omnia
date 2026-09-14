# Pipeline Modes & Domain Selection

Learn how to customize your Omnia deployments using pipeline modes and domain selection.

---

## Pipeline Modes

The pipeline supports three execution modes that control which stages run. Set the mode via `pipeline_mode` in `pipeline_config.yml` or the `CLUSTER1_PIPELINE_MODE` CI/CD variable.

### `default` — Full Cycle

Runs the complete lifecycle: setup the environment, clean up any previous deployment, rebuild the venv, deploy all selected domains, run tests, and generate a summary.

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

---

### `deploy` — Deploy Only

Skips cleanup and setup. Directly copies input files, fetches credentials from OpenBao, and runs the domain playbooks. Requires the Omnia venv to already exist on the target (from a previous `default` run or manual setup).

**Use when:** Pushing incremental updates, re-running a specific domain after changing input files, or redeploying after a credential rotation.

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

If the target does not have Omnia installed yet, add `enable_setup: "true"` to force the setup_environment stage:

```yaml
pipeline:
  pipeline_mode: "deploy"
  enable_setup: "true"
  domains: "orchestrator"
```

---

### `cleanup` — Tear Down

Runs domain-specific cleanup playbooks (`--tags cleanup`) and optionally runs `omnia.sh --cleanup --all` to destroy the venv and all data.

**Use when:** Decommissioning a server, resetting the environment before a fresh deployment, or cleaning up specific domains.

**Flow:**
```
initialization > setup_environment (if enable_setup) > cleanup_<domains> >
cleanup_omnia (only if domains=default) > summary
```

**Example — clean up everything:**
```yaml
pipeline:
  pipeline_mode: "cleanup"
  domains: "default"          # cleanup all domains + omnia venv
```

**Example — clean up only orchestrator:**
```yaml
pipeline:
  pipeline_mode: "cleanup"
  domains: "orchestrator"     # only cleanup orchestrator, keep others intact
```

---

## Domains

The pipeline manages 4 independent domains. Each domain has its own cleanup, deploy, and test stages. You can run all domains or select specific ones.

| Domain | Purpose | Credential file |
|---|---|---|
| **repo_manager** | Pulp-based package and repository management | `repo_manager_config_credentials.yml` |
| **image_build_manager** | Container image building and registry | `image_build_credentials.yml` |
| **orchestrator** | Kubernetes and container orchestration | `orchestrator_credentials.yml` |
| **telemetry** | Monitoring, logging, and observability | `telemetry_credentials.yml` |

### Domain Selection

Set via `domains` in `pipeline_config.yml` or the `CLUSTER1_DOMAINS` CI/CD variable. The value is treated as a **regex pattern** matched against each domain name.

| Setting | Domains that run | When to use |
|---|---|---|
| `"default"` | All 4 domains | Full deployment |
| `"repo_manager"` | repo_manager only | Initial repo setup or repo update |
| `"orchestrator"` | orchestrator only | Deploy/redeploy Kubernetes |
| `"telemetry"` | telemetry only | Deploy monitoring stack |
| `"image_build_manager"` | image_build_manager only | Deploy image builder |
| `"repo_manager\|orchestrator"` | repo_manager + orchestrator | Deploy two domains together |
| `"repo_manager\|image_build_manager\|telemetry"` | Three domains (skip orchestrator) | Everything except orchestrator |

---

## Real-World Scenarios

### Scenario 1: First-time full deployment with tests

```yaml
pipeline:
  pipeline_mode: "default"
  domains: "default"
  test_mode: "true"
```

Runs: Setup → Cleanup → Deploy all → Test all → Summary

---

### Scenario 2: Redeploy only repo_manager after changing Pulp credentials

```yaml
pipeline:
  pipeline_mode: "deploy"
  domains: "repo_manager"
  test_mode: "false"
```

Runs: Deploy repo_manager → Summary (fast, no cleanup or setup)

---

### Scenario 3: Clean up orchestrator, then redeploy it fresh

**Run 1: cleanup**
```yaml
pipeline:
  pipeline_mode: "cleanup"
  domains: "orchestrator"
```

**Run 2: deploy**
```yaml
pipeline:
  pipeline_mode: "deploy"
  domains: "orchestrator"
  enable_setup: "true"
```

---

### Scenario 4: Deploy repo_manager and telemetry together, skip others

```yaml
pipeline:
  pipeline_mode: "deploy"
  domains: "repo_manager|telemetry"
  test_mode: "true"
```

---

### Scenario 5: Full cleanup of everything on the target

```yaml
pipeline:
  pipeline_mode: "cleanup"
  domains: "default"
```

Runs all domain cleanups AND `omnia.sh --cleanup --all` which destroys the venv, `$OMNIA_DATA_PATH`, and `/etc/omnia/`.

---

### Scenario 6: Dry-run to preview what would happen

```yaml
pipeline:
  pipeline_mode: "default"
  domains: "default"
  dry_run: "true"
```

Logs all commands without executing any Ansible playbooks.

---

## Skipping Specific Domains

Use `skip_stages` to exclude domains without changing the `domains` setting. This is useful when `domains: "default"` but you want to temporarily skip one domain:

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

**Valid values for `skip_stages`:**
- `repo_manager`, `image_build_manager`, `orchestrator`, `telemetry` — skips cleanup + deploy + test for that domain
- `setup_environment`, `setup_main`, `cleanup_omnia` — skips that specific stage

---

## Pipeline Stages Reference

The pipeline runs these stages in order. Which stages actually execute depends on `PIPELINE_MODE`, `DOMAINS`, `TEST_MODE`, and `SKIP_STAGES`.

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

Legend:
- `Y` = stage runs
- `(opt)` = runs only if `ENABLE_SETUP=true`
- `(test)` = runs only if `TEST_MODE=true`

---

## What Each Stage Does

| Stage | Description |
|---|---|
| **initialization** | Loads cluster config from CI/CD variables, validates SSH connectivity, checks OpenBao reachability, writes `target.env` for downstream stages |
| **setup_environment** | Clones Omnia repo on target, copies `omnia.env`, runs `omnia.sh -s` to build venv, copies catalog file |
| **cleanup_\<domain\>** | Runs the domain's cleanup playbook (`--tags cleanup`). Non-fatal — first run has nothing to clean |
| **cleanup_omnia** | Runs `omnia.sh --cleanup --all` to destroy venv and data. Only runs when `DOMAINS=default` |
| **setup_main** | Rebuilds the venv after `cleanup_omnia` destroyed it. Re-copies `omnia.env` and catalog |
| **test_main_installation** | Installs the test venv and runs `run_validation.sh fvt_main verify` |
| **\<domain\>** | Copies input files to target, fetches credentials from OpenBao (JWT auth), encrypts with ansible-vault, runs the domain playbook |
| **test_\<domain\>** | Copies test config to target, installs test venv, runs domain validation tests. Non-fatal |
| **summary** | Generates a pipeline report and sends email notification |

---

## Next Steps

- [Configuration Reference](CONFIGURATION.md) — Explore all available settings
- [Troubleshooting](TROUBLESHOOTING.md) — Solve common issues
