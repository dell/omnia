# test_run_config.yml — Batch Execution Reference

Controls which scenarios run when using `./run_validation.sh --config` mode.
This file defines execution order, commands, marker filters, suite filters,
and per-scenario dataset overrides for automated batch runs.

---

## Usage

```bash
# Edit to enable/disable scenarios
vi test_run_config.yml

# Run all enabled scenarios in configured order
./run_validation.sh --config
```

---

## Global Options

| Field | Description | Default |
|-------|-------------|---------|
| `skip_on_failure` | Stop the current scenario on first test failure | `false` |
| `dataset_override` | Override dataset for ALL scenarios (takes precedence over per-scenario) | *(commented out)* |
| `sync_input_override` | Override `sync_image_build_input` for ALL scenarios | *(commented out)* |
| `sync_output_override` | Override `sync_output` for ALL scenarios | *(commented out)* |

---

## Scenario Configuration

Each scenario has the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `order` | int | Yes | Execution order (ascending). Must be unique across enabled scenarios. |
| `run` | bool | Yes | Enable (`true`) or disable (`false`) this scenario. |
| `command` | string | No | Execution mode: `deploy`, `verify`, or `test` (default: `test`). |
| `suite` | string | No | Subfolder filter inside the scenario. Empty = run all suites. |
| `marker` | string | No | Pytest marker filter expression. Empty = run all tests. |
| `dataset` | string | No | Override dataset from `test_config.yml` for this scenario only. |
| `sync_input` | bool | No | Override `sync_image_build_input` for this scenario. |
| `sync_output` | bool | No | Override `sync_output` for this scenario. |

### Command Modes

| Command | Description |
|---------|-------------|
| `deploy` | Run the Ansible playbook only (no verification tests) |
| `verify` | Run verification tests only (skip playbook deployment) |
| `test` | Full flow: deploy + verify (default) |

---

## Available Scenarios

| Scenario | Playbook Tag | Description |
|----------|-------------|-------------|
| `image_build_manager` | *(none — default: prepare + build)* | Full end-to-end deploy + verify |
| `validate` | `--tags validate` | Validate input configuration |
| `prepare` | `--tags prepare` | Deploy MinIO + registry infrastructure |
| `build` | `--tags build` | Build OS images (x86_64 + aarch64) |
| `cleanup` | `--tags cleanup` | Remove all deployed resources |

---

## Marker Expression Syntax

| Expression | Meaning |
|------------|---------|
| `sanity` | Tests with `@pytest.mark.sanity` |
| `x86_64,aarch64` | Tests with **either** marker (OR) |
| `x86_64+sanity` | Tests with **both** markers (AND) |

---

## Example — Full Pipeline

```yaml
skip_on_failure: false

scenarios:
  cleanup:
    order: 1
    run: true
    command: "test"
    suite: ""
    marker: "sanity"

  validate:
    order: 2
    run: true
    command: "test"
    suite: ""
    marker: "sanity"

  prepare:
    order: 3
    run: true
    command: "test"
    suite: ""
    marker: "sanity"

  build:
    order: 4
    run: true
    command: "test"
    suite: ""
    marker: "x86_64"

  image_build_manager:
    order: 5
    run: true
    command: "verify"
    suite: ""
    marker: "sanity"
```

## Example — Verify Only (No Deploy)

```yaml
scenarios:
  image_build_manager:
    order: 1
    run: true
    command: "verify"
    suite: "container"
    marker: "sanity"
```

## Example — Per-Scenario Dataset Override

```yaml
scenarios:
  prepare:
    order: 1
    run: true
    command: "test"
    suite: ""
    marker: "sanity"
    dataset: "my_custom_ds"
    sync_input: true
    sync_output: true
```
