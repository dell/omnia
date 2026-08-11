# Orchestrator — `test_run_config.yml` Reference

## Purpose

Defines batch test execution scenarios for `run_validation.sh --config`.

## Structure

```yaml
scenarios:
  <scenario_name>:
    run: true|false        # Enable/disable this scenario
    marker: "<expr>"       # Pytest marker filter (optional)
    suite: "<subfolder>"   # Restrict to suite subfolder (optional)
```

## Example

```yaml
scenarios:
  validate:
    run: true
    marker: "sanity"
    suite: ""

  prepare:
    run: true
    marker: ""
    suite: ""

  provision:
    run: false
    marker: ""
    suite: ""

  cleanup:
    run: false
    marker: ""
    suite: ""
```

## Usage

```bash
./run_validation.sh --config
```
