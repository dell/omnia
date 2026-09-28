# Utils Pipeline Documentation

## Overview

The **Utils Pipeline** is a specialized pipeline for executing utils domain operations on target servers. Unlike the main cluster pipeline which deploys and tests multiple domains (repo_manager, image_build_manager, orchestrator, telemetry), the utils pipeline focuses exclusively on utils domain tasks.

The utils pipeline runs independently and can be triggered separately from the main cluster pipeline by setting `UTILS_ENABLE=true` in your GitLab CI/CD variables.

---

## When to Use Utils Pipeline

Use the utils pipeline when you need to:

- **Collect logs** from deployed clusters (cluster logs + OIM logs)
- **Install OS** on target nodes using the install_os playbook
- **Backup OIM logs** independently
- **Run utils tests** to validate utils functionality

The utils pipeline does **NOT** run the main cluster pipeline stages (cleanup, deploy, test for other domains).

---

## Utils Modes

The `UTILS_MODE` variable controls which utils operations execute. Choose one:

### `default_logs` (Default)
- **Operations**: Collect both cluster and OIM logs
- **Stages**: `log_collection_cluster` + `log_collection_oim`
- **Use case**: Standard log collection after deployment
- **Example**: `UTILS_MODE=default_logs`

### `install_os`
- **Operations**: Run install_os playbook only
- **Stages**: `install_os`
- **Use case**: Install operating system on target nodes
- **Example**: `UTILS_MODE=install_os`

### `collect`
- **Operations**: Collect cluster logs only
- **Stages**: `log_collection_cluster`
- **Use case**: Collect logs from cluster domain only
- **Example**: `UTILS_MODE=collect`

### `backup_oim_logs`
- **Operations**: Backup OIM logs only
- **Stages**: `log_collection_oim`
- **Use case**: Backup OIM domain logs independently
- **Example**: `UTILS_MODE=backup_oim_logs`

---

## Pipeline Stages

The utils pipeline executes the following stages (in order):

```
1. initialization           Load cluster config, validate SSH connectivity
2. setup_environment        Clone omnia repo, copy omnia.env, setup venv
3. install_os              (conditional) Run utils.yml --tags install_os
4. log_collection_cluster  (conditional) Run utils.yml --tags collect
5. log_collection_oim      (conditional) Run utils.yml --tags backup_oim_logs
6. test_utils              (conditional) Run utils validation tests
7. summary                 Generate report, send email notification
```

**Conditional stages** run based on `UTILS_MODE` and `TEST_MODE`:

| Stage | Runs when |
|---|---|
| `install_os` | `UTILS_MODE == "install_os"` |
| `log_collection_cluster` | `UTILS_MODE == "default_logs"` OR `UTILS_MODE == "collect"` |
| `log_collection_oim` | `UTILS_MODE == "default_logs"` OR `UTILS_MODE == "backup_oim_logs"` |
| `test_utils` | `UTILS_ENABLE == "true"` AND `TEST_MODE == "true"` |

---

## Configuration

### Required Variables

Set these in your GitLab CI/CD variables or `pipeline_config.yml`:

| Variable | Default | Description |
|---|---|---|
| `UTILS_ENABLE` | `false` | Set to `"true"` to enable utils pipeline |
| `UTILS_MODE` | `default_logs` | Which utils operations to run |
| `TEST_MODE` | `false` | Set to `"true"` to run utils tests |
| `DRY_RUN` | `false` | Set to `"true"` to simulate without making changes |
| `VERBOSE` | `false` | Set to `"true"` for detailed Ansible output |

### Cluster-Specific Variables

For each cluster, set these variables (e.g., `CLUSTER1_*`):

| Variable | Description |
|---|---|
| `<CLUSTER>_TARGET_IP` | IP address of target server |
| `<CLUSTER>_TARGET_USER` | SSH username (default: `root`) |
| `<CLUSTER>_TARGET_PASS` | SSH password (masked variable) |
| `<CLUSTER>_OMNIA_REPO` | Omnia repository URL |
| `<CLUSTER>_OMNIA_BRANCH` | Git branch to clone |
| `<CLUSTER>_OMNIA_INSTALL_PATH` | Installation path on target |
| `<CLUSTER>_TEST_MODE` | Enable tests for this cluster |
| `<CLUSTER>_VERBOSE` | Verbose output for this cluster |
| `<CLUSTER>_DRY_RUN` | Dry-run mode for this cluster |

---

## Usage Examples

### Example 1: Collect Logs (Default)

```bash
UTILS_ENABLE=true
UTILS_MODE=default_logs
CLUSTER1_TEST_MODE=false
```

**Result**: Runs `initialization` → `setup_environment` → `log_collection_cluster` → `log_collection_oim` → `summary`

### Example 2: Install OS

```bash
UTILS_ENABLE=true
UTILS_MODE=install_os
CLUSTER1_TEST_MODE=false
```

**Result**: Runs `initialization` → `setup_environment` → `install_os` → `summary`

### Example 3: Collect Logs + Run Tests

```bash
UTILS_ENABLE=true
UTILS_MODE=default_logs
CLUSTER1_TEST_MODE=true
```

**Result**: Runs `initialization` → `setup_environment` → `log_collection_cluster` → `log_collection_oim` → `test_utils` → `summary`

### Example 4: Dry-Run Mode

```bash
UTILS_ENABLE=true
UTILS_MODE=default_logs
CLUSTER1_DRY_RUN=true
```

**Result**: Prints what would happen without executing any commands on the target server

---

## DRY_RUN Mode

When `DRY_RUN=true`, the pipeline simulates execution without making changes:

- ✅ SSH connectivity is tested
- ✅ Configuration is validated
- ✅ Ansible playbooks print what they would do
- ✅ Test setup steps are skipped
- ✅ Tests are not executed
- ✅ No files are copied to target
- ✅ No commands are executed on target

**Use case**: Validate pipeline configuration before actual execution

---

## Test Mode

When `TEST_MODE=true`, the `test_utils` stage runs after other stages complete.

The test stage:
1. Copies test input files to target
2. Installs test Python virtual environment
3. Runs utils validation tests

**Test configuration files** (optional):
- `clusters/<CLUSTER>/inputs/test/utils/test_config.yml`
- `clusters/<CLUSTER>/inputs/test/utils/test_run_config.yml`

**Test credentials** (optional):
- Set `<CLUSTER>_TEST_CREDS` as a GitLab CI/CD File Variable pointing to `test_creds.yml`

---

## Parent Pipeline Integration

The utils pipeline is triggered from the parent pipeline (`.gitlab-ci.yml`) when `UTILS_ENABLE=true`.

**Parent pipeline behavior**:
- If `UTILS_ENABLE=true`, the main cluster pipeline is **skipped**
- If `UTILS_ENABLE=false`, the main cluster pipeline runs normally
- Each cluster can have different settings

**Variables passed from parent to utils pipeline**:
- `CLUSTER` (cluster name)
- `OMNIA_REPO`, `OMNIA_BRANCH`, `OMNIA_INSTALL_PATH`
- `UTILS_MODE`, `UTILS_ENABLE`, `TEST_MODE`
- `VERBOSE`, `DRY_RUN`

---

## Email Notifications

When the utils pipeline completes, an email summary is sent (if configured).

The email includes:
- Pipeline status (success/failure)
- Cluster name and IP
- Commit SHA
- Stages executed
- Test results (if `TEST_MODE=true`)
- Links to pipeline and logs

**Email configuration**:
- Set `EMAIL_RECIPIENTS`, `EMAIL_SENDER`, `SMTP_SERVER`, `SMTP_PORT` in GitLab CI/CD variables
- See [EMAIL_NOTIFICATIONS.md](EMAIL_NOTIFICATIONS.md) for details

---

## Troubleshooting

### Utils pipeline not running

**Problem**: `UTILS_ENABLE=true` but utils pipeline doesn't start

**Solutions**:
1. Check `CLUSTERS` variable includes your cluster name
2. Verify `UTILS_ENABLE` is exactly `"true"` (string, not boolean)
3. Check parent pipeline rules in `.gitlab-ci.yml`

### Test stage not running

**Problem**: `TEST_MODE=true` but test stage is skipped

**Solutions**:
1. Verify `UTILS_ENABLE=true` (tests require utils pipeline enabled)
2. Check `<CLUSTER>_TEST_MODE` is set to `"true"`
3. Verify test input files exist at `clusters/<CLUSTER>/inputs/test/utils/`

### DRY_RUN not working

**Problem**: Commands still execute even with `DRY_RUN=true`

**Solutions**:
1. Check `<CLUSTER>_DRY_RUN` is set to `"true"` (not `GLOBAL_DRY_RUN`)
2. Verify variable is passed from parent pipeline
3. Check pipeline logs for DRY_RUN messages

### SSH connection fails

**Problem**: "SSH connection failed" error

**Solutions**:
1. Verify target IP is correct: `<CLUSTER>_TARGET_IP`
2. Check SSH user: `<CLUSTER>_TARGET_USER` (default: `root`)
3. Verify SSH password: `<CLUSTER>_TARGET_PASS` (masked variable)
4. Test SSH manually: `ssh -u <user> <ip>`
5. Check firewall allows port 22

### Playbook not found

**Problem**: "utils.yml not found" error

**Solutions**:
1. Verify `<CLUSTER>_OMNIA_INSTALL_PATH` is correct
2. Check `<CLUSTER>_OMNIA_BRANCH` exists in repository
3. Verify Omnia repository is accessible from target

---

## Advanced Topics

### Custom Test Commands

Modify test execution by setting environment variables in test stage:

```bash
export TEST_MARKER="sanity"  # Run only sanity tests
./run_validation.sh collect test --marker $TEST_MARKER
```

### Verbose Ansible Output

Set `VERBOSE=true` to see detailed Ansible output:

```
UTILS_ENABLE=true
CLUSTER1_VERBOSE=true
```

This adds `-vvv` flag to all Ansible playbook commands.

### Multi-Cluster Utils Pipeline

Run utils operations on multiple clusters simultaneously:

```bash
UTILS_ENABLE=true
CLUSTERS=cluster1,cluster2,cluster3
UTILS_MODE=default_logs
```

Each cluster runs independently in parallel.

---

## Related Documentation

- [Pipeline_Guide.md](Pipeline_Guide.md) - Complete pipeline guide
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration reference
- [PIPELINE_MODES.md](PIPELINE_MODES.md) - Main pipeline modes
- [EMAIL_NOTIFICATIONS.md](EMAIL_NOTIFICATIONS.md) - Email setup
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - General troubleshooting
