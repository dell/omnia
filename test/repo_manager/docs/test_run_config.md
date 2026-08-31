# Test Run Configuration

The `test_run_config.yml` file defines batch test execution scenarios.

## Structure

```yaml
scenarios:
  - validate
  - prepare
  - execute
  - status
```

## Usage

Run all scenarios from config:

```bash
./run_validation.sh --config
```
