# test_run_config.yml — Batch Execution Reference

Controls which scenarios run when using `./run_validation.sh --config` mode.
This file defines execution order, marker filters, and suite filters for
automated batch runs.

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

---

## Scenario Configuration

Each scenario has the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `order` | int | Execution order (ascending). Must be unique across enabled scenarios. |
| `run` | bool | Enable (`true`) or disable (`false`) this scenario. |
| `suite` | string | Subfolder filter inside the scenario. Empty = run all suites. |
| `marker` | string | Pytest marker filter expression. Empty = run all tests. |

---

## Available Scenarios

| Scenario | Playbook Tag | Description |
|----------|-------------|-------------|
| `repo_manager` | *(none)* | Full verification — no deploy, verify only |
| `validate` | `--tags validate` | Validate input configuration |
| `deploy` | `--tags deploy` | Deploy Pulp container and infrastructure |
| `download` | `--tags download` | Download and sync RPM repositories |
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
    suite: ""
    marker: "sanity"

  validate:
    order: 2
    run: true
    suite: ""
    marker: "sanity"

  deploy:
    order: 3
    run: true
    suite: ""
    marker: "sanity"

  download:
    order: 4
    run: true
    suite: ""
    marker: "x86_64"

  repo_manager:
    order: 5
    run: true
    suite: ""
    marker: "sanity"
```

## Example — Verify Only

```yaml
scenarios:
  repo_manager:
    order: 1
    run: true
    suite: "pulp"
    marker: "sanity"
```
