# Build Stream Pipeline Documentation

## Overview

The **Build Stream Pipeline** is a specialized pipeline for deploying and testing the build_stream domain on target servers. Unlike the main cluster pipeline which deploys all domains sequentially (repo_manager, image_build_manager, orchestrator, telemetry), the build stream pipeline uses a unified `prepare_base` stage to set up the base infrastructure (repo_manager, image_build_manager, orchestrator) and then deploys the build_stream domain.

The build stream pipeline runs independently and can be triggered separately from the main cluster pipeline by setting `BUILD_STREAM_ENABLE=true` in your GitLab CI/CD variables.

---

## When to Use Build Stream Pipeline

Use the build stream pipeline when you need to:

- **Deploy build_stream domain** with a unified base infrastructure setup
- **Prepare base infrastructure** (repo_manager, image_build_manager, orchestrator) using a single `prepare_base` stage
- **Test base domains** (repo_manager, image_build_manager, orchestrator) before build_stream deployment
- **Deploy and test build_stream** after base infrastructure is ready
- **Skip the standard cluster pipeline** and use the optimized build stream flow

The build stream pipeline does **NOT** run the main cluster pipeline stages. When `BUILD_STREAM_ENABLE=true`, the cluster and utils pipelines are skipped.

---

## Key Differences from Cluster Pipeline

| Aspect | Cluster Pipeline | Build Stream Pipeline |
|--------|------------------|----------------------|
| **Base Setup** | Individual deploy stages for each domain | Single `prepare_base` stage for all base domains |
| **Base Domains** | repo_manager, image_build_manager, orchestrator deployed separately | All three prepared together in `prepare_base` |
| **Domains Deployed** | repo_manager, image_build_manager, orchestrator, telemetry | repo_manager, image_build_manager, orchestrator, build_stream |
| **Telemetry** | Deployed as a domain | Not included in build stream pipeline |
| **Use Case** | General-purpose multi-domain deployment | Build stream-focused deployments |

---

## Pipeline Stages

The build stream pipeline executes the following stages (in order):

```
1. initialization              Load cluster config, validate SSH connectivity
2. setup_environment           Clone omnia repo, copy omnia.env, setup venv
3. cleanup_build_stream        (conditional) Run build_stream cleanup
4. cleanup_<domains>           (conditional) Run domain cleanups
5. cleanup_omnia               (conditional) Run omnia cleanup
6. setup_main                  (conditional) Rebuild venv after cleanup
7. test_main_installation      (conditional) Run main validation tests
8. prepare_base                (conditional) Prepare base infrastructure (repo_manager, image_build_manager, orchestrator)
9. test_repo_manager           (conditional) Run repo_manager tests
10. test_image_build_manager   (conditional) Run image_build_manager tests
11. test_orchestrator          (conditional) Run orchestrator tests
12. build_stream               (conditional) Deploy build_stream domain
13. test_build_stream          (conditional) Run build_stream tests
14. summary                    Generate report, send email notification
```

**Conditional stages** run based on `PIPELINE_MODE`, `DOMAINS`, `TEST_MODE`, and `SKIP_STAGES`:

| Stage | Runs when |
|-------|-----------|
| `cleanup_*` | `PIPELINE_MODE == "cleanup"` OR `PIPELINE_MODE == "default"` |
| `cleanup_omnia` | `PIPELINE_MODE == "cleanup"` OR `PIPELINE_MODE == "default"` AND `DOMAINS == "default"` |
| `setup_main` | `PIPELINE_MODE == "default"` (after cleanup_omnia) |
| `test_main_installation` | `PIPELINE_MODE == "deploy"` OR `PIPELINE_MODE == "default"` AND `TEST_MODE == "true"` |
| `prepare_base` | `PIPELINE_MODE == "deploy"` OR `PIPELINE_MODE == "default"` |
| `test_<domain>` | `PIPELINE_MODE == "deploy"` OR `PIPELINE_MODE == "default"` AND `TEST_MODE == "true"` AND domain matches `DOMAINS` |
| `build_stream` | `PIPELINE_MODE == "deploy"` OR `PIPELINE_MODE == "default"` AND `DOMAINS` matches `build_stream` |
| `test_build_stream` | `PIPELINE_MODE == "deploy"` OR `PIPELINE_MODE == "default"` AND `TEST_MODE == "true"` AND `DOMAINS` matches `build_stream` |

---

## `prepare_base` Stage

The `prepare_base` stage is the key difference from the cluster pipeline. It prepares the base infrastructure for build_stream by:

1. **Copying input files** for repo_manager, image_build_manager, and orchestrator to the target
2. **Fetching credentials** from OpenBao for all three domains
3. **Encrypting credentials** with ansible-vault
4. **Running `omnia.sh --prepare-base`** to execute base domain setup

This unified approach is more efficient than deploying each domain separately and allows for coordinated base infrastructure setup.

---

## Configuration

### Required Variables

Set these in your GitLab CI/CD variables or `pipeline_config.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `BUILD_STREAM_ENABLE` | `false` | Set to `"true"` to enable build stream pipeline |
| `PIPELINE_MODE` | `default` | Pipeline mode: `default`, `deploy`, or `cleanup` |
| `DOMAINS` | `default` | Which domains to run (regex pattern) |
| `TEST_MODE` | `false` | Set to `"true"` to run validation tests |
| `DRY_RUN` | `false` | Set to `"true"` to simulate without making changes |
| `VERBOSE` | `false` | Set to `"true"` for detailed Ansible output |

### Cluster-Specific Variables

For each cluster, set these variables (e.g., `CLUSTER1_*`):

| Variable | Description |
|----------|-------------|
| `<CLUSTER>_TARGET_IP` | IP address of target server |
| `<CLUSTER>_TARGET_USER` | SSH username (default: `root`) |
| `<CLUSTER>_TARGET_PASS` | SSH password (masked in GitLab) |
| `<CLUSTER>_OMNIA_REPO` | Omnia Git repository URL |
| `<CLUSTER>_OMNIA_BRANCH` | Git branch to clone |
| `<CLUSTER>_OMNIA_INSTALL_PATH` | Installation path on target |
| `<CLUSTER>_BAO_SERVER_URL` | OpenBao server URL |
| `<CLUSTER>_BAO_AUTH_ROLE` | OpenBao JWT role |
| `<CLUSTER>_BAO_DATA_PATH` | OpenBao secret path |
| `<CLUSTER>_PIPELINE_MODE` | Pipeline mode |
| `<CLUSTER>_DOMAINS` | Domain selection |
| `<CLUSTER>_ENABLE_SETUP` | Force setup in deploy/cleanup modes |
| `<CLUSTER>_ENABLE_DISCOVERY` | Enable discovery stage |
| `<CLUSTER>_TEST_MODE` | Enable test stages |
| `<CLUSTER>_DRY_RUN` | Dry-run mode |
| `<CLUSTER>_VERBOSE` | Verbose logging |
| `<CLUSTER>_REPO_MANAGER_TAGS` | Ansible tags for repo_manager |
| `<CLUSTER>_IMAGE_BUILD_MANAGER_TAGS` | Ansible tags for image_build_manager |
| `<CLUSTER>_ORCHESTRATOR_TAGS` | Ansible tags for orchestrator |
| `<CLUSTER>_DISCOVERY_TAGS` | Ansible tags for discovery |
| `<CLUSTER>_BUILD_STREAM_TAGS` | Ansible tags for build_stream |
| `<CLUSTER>_TEST_MAIN_CMD` | Test command for main |
| `<CLUSTER>_TEST_REPO_MANAGER_CMD` | Test command for repo_manager |
| `<CLUSTER>_TEST_IMAGE_BUILD_MANAGER_CMD` | Test command for image_build_manager |
| `<CLUSTER>_TEST_ORCHESTRATOR_CMD` | Test command for orchestrator |
| `<CLUSTER>_TEST_DISCOVERY_CMD` | Test command for discovery |
| `<CLUSTER>_TEST_BUILD_STREAM_CMD` | Test command for build_stream |
| `<CLUSTER>_SKIP_STAGES` | Stages to skip |

---

## Examples

### Example 1: Full build stream deployment with tests

```yaml
global:
  build_stream_enable: "true"

cluster1:
  pipeline:
    pipeline_mode: "default"
    domains: "default"
    test_mode: "true"
```

**Flow:**
1. Initialize
2. Setup environment
3. Cleanup all domains (if first run)
4. Prepare base infrastructure (repo_manager, image_build_manager, orchestrator)
5. Test base domains
6. Deploy build_stream
7. Test build_stream
8. Summary

---

### Example 2: Deploy only build_stream (base already exists)

```yaml
global:
  build_stream_enable: "true"

cluster1:
  pipeline:
    pipeline_mode: "deploy"
    domains: "build_stream"
    test_mode: "true"
```

**Flow:**
1. Initialize
2. Prepare base infrastructure (repo_manager, image_build_manager, orchestrator)
3. Test base domains
4. Deploy build_stream
5. Test build_stream
6. Summary

---

### Example 3: Clean up build_stream only

```yaml
global:
  build_stream_enable: "true"

cluster1:
  pipeline:
    pipeline_mode: "cleanup"
    domains: "build_stream"
```

**Flow:**
1. Initialize
2. Setup environment
3. Cleanup build_stream
4. Summary

---

### Example 4: Deploy with custom Ansible tags

```yaml
global:
  build_stream_enable: "true"

cluster1:
  pipeline:
    pipeline_mode: "deploy"
    domains: "default"
    test_mode: "true"
  deploy_tags:
    repo_manager: "deploy"
    image_build_manager: "deploy"
    orchestrator: "deploy"
    build_stream: "deploy"
```

---

### Example 5: Custom test commands

```yaml
global:
  build_stream_enable: "true"

cluster1:
  pipeline:
    pipeline_mode: "deploy"
    domains: "default"
    test_mode: "true"
  test_commands:
    repo_manager: "./run_validation.sh fvt_repo_manager verify --marker sanity"
    image_build_manager: "./run_validation.sh fvt_image_build_manager verify --marker sanity"
    orchestrator: "./run_validation.sh fvt_orchestrator verify --marker sanity"
    build_stream: "./run_validation.sh fvt_build_stream test --marker sanity"
```

---

## Input Files

The build stream pipeline requires input files for each domain:

```
clusters/cluster1/inputs/
├── omnia.env                           Omnia environment config
├── repo_manager/                       repo_manager input files
├── image_build_manager/                image_build_manager input files
├── orchestrator/                       orchestrator input files
├── build_stream/                       build_stream input files
└── test/
    ├── repo_manager/
    │   ├── test_config.yml
    │   └── test_run_config.yml
    ├── image_build_manager/
    │   ├── test_config.yml
    │   └── test_run_config.yml
    ├── orchestrator/
    │   ├── test_config.yml
    │   └── test_run_config.yml
    └── build_stream/
        ├── test_config.yml
        └── test_run_config.yml
```

All input files are collected from the Omnia source tree by `setup_gitlab_project.py --create`.

---

## Credentials

The build stream pipeline fetches credentials from OpenBao for each domain:

| Domain | Secret Path | Credential File |
|--------|-------------|-----------------|
| repo_manager | `<BAO_DATA_PATH>/repo_manager` | `repo_manager_config_credentials.yml` |
| image_build_manager | `<BAO_DATA_PATH>/image_build_manager` | `image_build_credentials.yml` |
| orchestrator | `<BAO_DATA_PATH>/orchestrator` | `orchestrator_credentials.yml` |
| build_stream | `<BAO_DATA_PATH>/build_stream` | `build_stream_credentials.yml` |

Credentials are encrypted with ansible-vault before being copied to the target.

For OpenBao setup instructions, see [OpenBao Setup Guide](OPENBAO_SETUP.md).

---

## Troubleshooting

### Build stream pipeline doesn't trigger

**Problem:** Pipeline runs cluster pipeline instead of build stream pipeline.

**Solution:** Ensure `BUILD_STREAM_ENABLE=true` is set in GitLab CI/CD variables or `pipeline_config.yml`.

### prepare_base stage fails

**Problem:** `prepare_base` stage fails with credential or input file errors.

**Solution:**
1. Verify OpenBao is reachable and credentials are stored at `<BAO_DATA_PATH>/repo_manager`, `<BAO_DATA_PATH>/image_build_manager`, `<BAO_DATA_PATH>/orchestrator`
2. Verify input files exist in `clusters/<cluster>/inputs/repo_manager/`, `clusters/<cluster>/inputs/image_build_manager/`, `clusters/<cluster>/inputs/orchestrator/`
3. Check SSH connectivity to target server
4. Enable `VERBOSE=true` for detailed Ansible output

### Tests fail after prepare_base

**Problem:** Base domain tests fail after `prepare_base` completes.

**Solution:**
1. Check test configuration files in `clusters/<cluster>/inputs/test/<domain>/test_config.yml`
2. Verify test credentials are available (set via `<CLUSTER>_TEST_CREDS` CI/CD File Variable or OpenBao)
3. Check test output in pipeline logs
4. Run tests manually on target to debug

### build_stream deployment fails

**Problem:** `build_stream` stage fails after base infrastructure is ready.

**Solution:**
1. Verify build_stream input files exist in `clusters/<cluster>/inputs/build_stream/`
2. Verify build_stream credentials are stored in OpenBao at `<BAO_DATA_PATH>/build_stream`
3. Check SSH connectivity to target
4. Enable `VERBOSE=true` for detailed Ansible output
5. Check `omnia.sh --prepare-base` output on target

---

## Next Steps

- [Configuration Reference](CONFIGURATION.md) — Explore all available settings
- [Pipeline Modes & Domains](PIPELINE_MODES.md) — Learn deployment strategies
- [OpenBao Setup Guide](OPENBAO_SETUP.md) — Set up credential management
- [Troubleshooting Guide](TROUBLESHOOTING.md) — Solve common issues
