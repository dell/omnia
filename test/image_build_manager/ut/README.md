# Image Build Manager Unit Tests

The unit-test suite validates schemas, catalogs, package mappings, driver-group
exclusion, and standalone role contracts without deploying Image Build
Manager.

## Test identification

Each existing unit test has a stable ID in the range `IBM_UT_001` through
`IBM_UT_073`. The centralized mapping is maintained in
`library/vars/ut_test_case_vars.py`; pytest method names remain descriptive
and unchanged.

| ID range | Test file | Coverage |
|----------|-----------|----------|
| `IBM_UT_001`–`014` | `test_catalog_validation.py` | Catalog schema and sample catalog structure |
| `IBM_UT_015`–`032` | `test_driver_group_skip.py` | Driver-group detection and package exclusion |
| `IBM_UT_033`–`044` | `test_functional_group_packages.py` | Functional-group package structure and content |
| `IBM_UT_045`–`057` | `test_standalone_independence.py` | Standalone role dependencies and repository structure |
| `IBM_UT_058`–`073` | `test_validate_image_build_config.py` | Image-build configuration, repository status, and input files |

The runner resolves each ID from the test file, class, and method portion of
the pytest node ID and displays it in the summary and generated reports.
Parameterized variants of one method intentionally share that method's ID.
Every mapping stores its ID explicitly, so source reordering cannot renumber
published cases. Append new mappings with the next available ID.

## Execution

Run the complete suite from `test/image_build_manager/`:

```bash
./run_validation.sh ut_image_build_manager test
```
