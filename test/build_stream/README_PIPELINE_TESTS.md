# Pipeline Tests — Running Guide

## Quick Start

**All pipeline tests MUST be run with the venv Python interpreter:**

```bash
cd /home/omnia2100rc2/omnia/ansible_collections/dell/4849_issue/test/build_stream

# Run all pipeline tests
./.venv/bin/python -m pytest fvt/build_stream/pipeline/ -v

# Run a specific test
./.venv/bin/python -m pytest fvt/build_stream/pipeline/test_autotrigger_pipeline.py -v

# Run with markers
./.venv/bin/python -m pytest -m pipeline -v
```

## Test Execution Order

Tests are ordered by `@pytest.mark.order(n)`:

| Order | Suite | Tests | Description |
|-------|-------|-------|-------------|
| 0-100 | infrastructure/ | 6 | Container, API, DB, GitLab checks (prerequisite) |
| 200 | pipeline/ | 13 | Auto-trigger build pipeline |
| 250 | pipeline/ | 4 | Generated input verification |
| 300 | pipeline/ | 7 | Manual deploy pipeline |
| 400 | pipeline/ | 7 | Cleanup pipeline |
| 500 | stress/ | 1 | Stress: repeated builds |
| 600 | stress/ | 1 | Stress: cleanup all groups |
| 700 | stress/ | 1 | Stress: build → cleanup → rebuild |

## Test Dependencies

Tests use **module-level state** to pass context between tests:

```python
_pipeline_state = {
    "pipeline_id": 0,
    "job_id": "",
    "build_success": False,
}
```

**Dependent tests skip if earlier tests fail:**
- `test_core_stage_completion[*]` skips if `test_trigger_build_pipeline` fails
- `test_verify_registry_images` skips if `test_catalog_roles` fails
- Deploy/cleanup tests skip if no image groups exist

This is **intentional** — tests are designed to fail fast and skip dependent tests.

## Current Test Status (as of Aug 11, 2026)

```
5 passed, 2 failed, 24 skipped / 31 total
```

### Passing ✅
- `test_trigger_build_pipeline` — Catalog uploaded, pipeline triggered
- `test_clone_omnia_repo` — Omnia repo cloned for comparison
- `test_software_config_readable` — Config file read from container
- `test_verify_generated_inputs` — Generated inputs match source
- `test_cleanup_clone` — Temp clone cleaned up

### Failing ❌
- `test_trigger_deploy_pipeline` — **PXE mapping file not found (404)**
- `test_trigger_cleanup_pipeline` — **No image groups in database**

### Skipped ⏭️
24 tests skipped because they depend on earlier tests passing (correct behavior)

## Fixing the Failures

### 1. PXE Mapping File Missing

**Error:** `Failed to commit PXE mapping file: PXE mapping file not found: 404 File Not Found`

**Fix:** Create a PXE mapping file in the test dataset:

```bash
cat > /home/omnia2100rc2/omnia/ansible_collections/dell/4849_issue/test/build_stream/datasets/data_set_01/input/pxe_mapping_file.csv << 'EOF'
hostname,mac_address,ip_address,subnet_mask,gateway,dns_servers
node1,00:11:22:33:44:55,192.168.1.10,255.255.255.0,192.168.1.1,8.8.8.8
node2,00:11:22:33:44:56,192.168.1.11,255.255.255.0,192.168.1.1,8.8.8.8
EOF
```

Then sync the dataset:
```bash
./.venv/bin/python -m pytest fvt/build_stream/pipeline/test_manual_pipeline.py::TestManualDeployPipeline::test_trigger_deploy_pipeline -v
```

### 2. Image Groups Missing

**Error:** `Failed to trigger cleanup pipeline: Failed to get image groups: psql query failed (rc=2)`

**Fix:** This error occurs because the cleanup pipeline needs image groups from a successful build. The build pipeline must complete first:

```bash
# Run build pipeline first
./.venv/bin/python -m pytest fvt/build_stream/pipeline/test_autotrigger_pipeline.py -v

# Then run cleanup
./.venv/bin/python -m pytest fvt/build_stream/pipeline/test_cleanup_pipeline.py -v
```

## Environment Setup

### Prerequisites
1. **Target system** must have build_stream deployed with `enable_build_stream: true`
2. **Infrastructure tests** must pass (containers, API, DB running)
3. **Python venv** must be activated (or use `.venv/bin/python`)

### Verify Setup
```bash
# Check if build_stream is enabled on target
./.venv/bin/python -c "
from library.functions import is_build_stream_enabled
from omnia_auto import get_testinfra_host
host = get_testinfra_host()
print('build_stream enabled:', is_build_stream_enabled(host))
"

# Run infrastructure tests first
./.venv/bin/python -m pytest fvt/build_stream/infrastructure/ -v
```

## Troubleshooting

### ModuleNotFoundError: No module named 'omnia_auto'
**Solution:** Use the venv Python interpreter:
```bash
./.venv/bin/python -m pytest ...
```

### Tests skip with "build_stream is not enabled"
**Solution:** Ensure `enable_build_stream: true` in `/opt/omnia/build_stream/input/project_default/build_stream_config.yml`

### Tests fail with "container not found"
**Solution:** Run infrastructure tests first to deploy containers:
```bash
./.venv/bin/python -m pytest fvt/build_stream/infrastructure/ -v
```

### Database query fails
**Solution:** Ensure PostgreSQL container is running and initialized:
```bash
podman ps | grep omnia_postgres
podman logs omnia_postgres
```

## Test Data Location

Test datasets are synced from:
```
/home/omnia2100rc2/omnia/ansible_collections/dell/4849_issue/test/build_stream/datasets/data_set_01/input/
```

To:
```
/opt/omnia/build_stream/input/project_default/
```

Add any required test files (like `pxe_mapping_file.csv`) to the `datasets/data_set_01/input/` directory.

## Notes

- Tests use `@pytest.mark.order(n)` for execution order
- Module-level state is shared across tests in the same file
- Tests intentionally skip if dependencies fail (fail-fast design)
- All tests require a live target system with build_stream deployed
- Pipeline tests are **integration tests** — they trigger real pipelines on the target
