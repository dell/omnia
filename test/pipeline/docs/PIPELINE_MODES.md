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
initialization > cleanup_<domains> > test_cleanup_<domains> > cleanup_omnia >
setup_main > test_main_installation > <domains> > test_<domains> > summary
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

If the target does not have Omnia installed yet, add `enable_setup: "true"` to run the install (`setup_main`: `omnia.sh -s`) in this mode:

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
initialization > cleanup_<domains> > test_cleanup_<domains> > cleanup_omnia (only if domains=default) > summary
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

The pipeline manages 6 independent domains. Each domain has its own cleanup, deploy, and test stages. You can run all domains or select specific ones.

| Domain | Purpose | Credential file |
|---|---|---|
| **repo_manager** | Pulp-based package and repository management | `repo_manager_config_credentials.yml` |
| **image_build_manager** | Container image building and registry | `image_build_credentials.yml` |
| **discovery** | Network and hardware discovery | `discovery_credentials.yml` |
| **orchestrator** | Kubernetes and container orchestration | `orchestrator_credentials.yml` |
| **telemetry** | Monitoring, logging, and observability | `telemetry_credentials.yml` |
| **build_stream** | Build stream image provisioning and deployment | `build_stream_credentials.yml` |

### Domain Selection

Set via `domains` in `pipeline_config.yml` or the `CLUSTER1_DOMAINS` CI/CD variable. The value is treated as a **regex pattern** matched against each domain name.

| Setting | Domains that run | When to use |
|---|---|---|
| `"default"` | All 6 domains | Full deployment |
| `"repo_manager"` | repo_manager only | Initial repo setup or repo update |
| `"orchestrator"` | orchestrator only | Deploy/redeploy Kubernetes |
| `"discovery"` | discovery only | Deploy network/hardware discovery |
| `"telemetry"` | telemetry only | Deploy monitoring stack |
| `"image_build_manager"` | image_build_manager only | Deploy image builder |
| `"build_stream"` | build_stream only | Deploy build stream images |
| `"repo_manager\|orchestrator"` | repo_manager + orchestrator | Deploy two domains together |
| `"repo_manager\|image_build_manager\|telemetry"` | Three domains (skip orchestrator & build_stream) | Subset of domains |

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
- `repo_manager`, `image_build_manager`, `discovery`, `orchestrator`, `telemetry`, `build_stream` — skips cleanup + deploy + test for that domain
- `setup_main`, `test_main_installation`, `cleanup_omnia` — skips that specific stage
- `nfs_check` — skips the NFS check inside `initialization`; `inputs` — skips the input copy inside `setup_main`

---

## Pipeline Stages Reference

The pipeline runs these stages in order. Which stages actually execute depends on `PIPELINE_MODE`, `DOMAINS`, `TEST_MODE`, and `SKIP_STAGES`.

```
 Stage                         Mode: default   deploy   cleanup
 ─────────────────────────────────────────────────────────────────
 1. initialization                    Y          Y     Y
 2. cleanup_build_stream              Y                Y
 3. test_cleanup_build_stream         Y                Y
 4. cleanup_utils                     Y                Y
 5. test_cleanup_utils                Y                Y
 6. cleanup_telemetry                 Y                Y
 7. test_cleanup_telemetry            Y                Y
 8. cleanup_orchestrator              Y                Y
 9. test_cleanup_orchestrator         Y                Y
10. cleanup_discovery                 Y                Y
11. test_cleanup_discovery            Y                Y
12. cleanup_image_build_manager       Y                Y
13. test_cleanup_image_build_manager  Y                Y
14. cleanup_repo_manager              Y                Y
15. test_cleanup_repo_manager         Y                Y
16. cleanup_omnia                     Y                Y  (DOMAINS=default)
17. setup_main                        Y       (inputs) (opt)
18. test_main_installation          (test)     (test)
19. repo_manager                      Y          Y
20. test_repo_manager               (test)     (test)
21. image_build_manager               Y          Y
22. test_image_build_manager        (test)     (test)
23. discovery                       (disc)     (disc)
24. test_discovery               (disc+test)  (disc+test)
25. orchestrator                      Y          Y
26. test_orchestrator               (test)     (test)
27. telemetry                         Y          Y
28. test_telemetry                  (test)     (test)
29. summary                           Y          Y     Y
```

A failed cleanup or cleanup test does not stop the other ones, but `cleanup_omnia`, the install and every later stage are skipped and `summary` runs and fails the pipeline. Each `test_cleanup_<domain>` runs right after its `cleanup_<domain>` and has the same domain selection.
See [CLUSTER_PIPELINE.md](CLUSTER_PIPELINE.md) for how each stage works.

Legend:
- `Y` = stage runs
- `(opt)` = runs only if `ENABLE_SETUP=true` (install only)
- `(inputs)` = in `deploy` mode `setup_main` only copies the inputs (no install)
- `(test)` = runs only if `TEST_MODE=true`
- `(disc)` = runs only if `ENABLE_DISCOVERY=true` and domain matches
- `(disc+test)` = runs only if `ENABLE_DISCOVERY=true`, `TEST_MODE=true`, and domain matches

---

## What Each Stage Does

| Stage | Description |
|---|---|
| **initialization** | One stage: the clone of Omnia on the OIM and the pipeline helpers taken from it, the checks of the CI/CD variables, the OIM host key, the input folders and SSH, the commit and `omnia.env`, and (`DOMAINS=default`) the read-only NFS check, so an unreachable share stops the run before anything is deleted. Nothing secret is written to an artifact |
| **cleanup_\<domain\>** | Runs the cleanup playbook with `./omnia.sh --run <domain> --tags <cleanup tag>` in the Omnia venv, with the flags of the cluster's `test_config.yml`; no test runs. Every cleanup runs even after one failed; nothing is installed after a failure. First run: nothing to clean |
| **test_cleanup_\<domain\>** | Runs `fvt_<domain> cleanup verify` in the Omnia venv (utils: only its combined cleanup tests) with the pipeline id as the report id. The orchestrator one also empties the Slurm and K8s NFS shares. Needs the marker of its cleanup |
| **cleanup_omnia** | Runs `omnia.sh --cleanup --all`. Not run when `cleanup_orchestrator` or `test_cleanup_orchestrator` failed (the latter empties the Slurm and K8s NFS shares). Only runs when `DOMAINS=default` |
| **setup_main** | Runs `omnia.sh -s` (the Omnia venv and every `domain-init`) in `default` mode or with `ENABLE_SETUP=true`, then copies `clusters/<name>/inputs/src/<domain>/` of every deploy domain and the catalog to the OIM in `default` and `deploy` mode |
| **test_main_installation** | Runs `run_validation.sh fvt_main verify` in the Omnia venv |
| **\<domain\>** | Fetches the domain credentials from OpenBao (JWT auth), encrypts them with ansible-vault, runs every playbook tag one by one with `./omnia.sh --run <domain> --tags <tag>`. A failure stops the pipeline |
| **test_\<domain\>** | Copies the test config and credentials to the OIM and runs the verify command in the Omnia venv. A failure does not stop the next domain; it does not run when the domain exec failed |
| **discovery** | As `<domain>`, after image_build_manager. Only runs when `ENABLE_DISCOVERY=true` and the domain matches |
| **summary** | Generates a pipeline report and sends email notification |

---

## Next Steps

- [Configuration Reference](CONFIGURATION.md) — Explore all available settings
- [Troubleshooting](TROUBLESHOOTING.md) — Solve common issues
