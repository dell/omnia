# Discovery Unit Tests

The unit-test suite validates schemas, input configuration, credential
rules, L2 semantic validators, and standalone role contracts without
deploying Discovery.

## Test identification

Each unit-test method has a stable ID in the range `DISC_UT_001` through
`DISC_UT_040`. The centralized mapping is maintained in
`library/vars/ut_test_case_vars.py`; pytest method names remain descriptive
and unchanged.

| ID range | Test file | Coverage |
|----------|-----------|----------|
| `DISC_UT_001`--`006` | `test_input_validation_schema.py` | Schema file existence and structure |
| `DISC_UT_007`--`014` | `test_input_validation_schema.py` | discovery_config.json schema validation |
| `DISC_UT_015`--`020` | `test_input_validation_schema.py` | Credential rules schema validation |
| `DISC_UT_021`--`030` | `test_discovery_config_validator.py` | L2 semantic validation (OME IP) |
| `DISC_UT_031`--`040` | `test_standalone_independence.py` | Standalone independence and repo structure |

The runner resolves each ID from the test file, class, and method portion of
the pytest node ID and displays it in the summary and generated reports.
Parameterized variants of one method intentionally share that method's ID.
Every mapping stores its ID explicitly, so source reordering cannot renumber
published cases. Append new mappings with the next available ID.

## Execution

Run the complete suite from `test/discovery/`:

```bash
./run_validation.sh ut_discovery test
```
