# Image Build Manager Unit Tests

The unit-test suite validates schemas, catalogs, package mappings, driver-group
exclusion, and standalone role contracts without deploying Image Build
Manager.

## Test identification

Each unit-test method has a stable ID in the range `IMGBM_UT_001` through
`IMGBM_UT_151`. The centralized mapping is maintained in
`library/vars/ut_test_case_vars.py`; pytest method names remain descriptive
and unchanged.

| ID range | Test file | Coverage |
|----------|-----------|----------|
| `IMGBM_UT_001`–`014` | `test_catalog_validation.py` | Catalog schema and sample catalog structure |
| `IMGBM_UT_015`–`032` | `test_driver_group_skip.py` | Driver-group detection and package exclusion |
| `IMGBM_UT_033`–`044` | `test_functional_group_packages.py` | Functional-group package structure and content |
| `IMGBM_UT_045`–`057` | `test_standalone_independence.py` | Standalone role dependencies and repository structure |
| `IMGBM_UT_058`–`073` | `test_validate_image_build_config.py` | Image-build configuration, repository status, and input files |
| `IMGBM_UT_074`–`110` | `test_input_validation_schema.py` | Strict types and required values, S3 provider rules, optional AArch64 IPv4, package-group schema, and build-only repo-status contract |
| `IMGBM_UT_111`–`113` | `test_parse_repo_status.py` | Version-aware parsing and optional Repo Manager metadata |
| `IMGBM_UT_114` | `test_driver_group_skip.py` | RHEL 10.2 catalog resolution for supported architectures |
| `IMGBM_UT_115`–`126` | `test_image_group_dictionary.py` | Persistent image dictionary behavior and validation |
| `IMGBM_UT_127`–`136` | `test_catalog_rebuild_contract.py` | Catalog rebuild, cache, hash, and status contracts |
| `IMGBM_UT_137`–`139` | `test_s3_artifact_layout.py` | Thrillhouse legacy/versioned boot artifact layout validation |
| `IMGBM_UT_140`–`144` | `test_catalog_reuse_state.py` | Catalog-reuse state restoration and interrupted-run recovery |
| `IMGBM_UT_145`–`148` | `test_runner_lifecycle_safety.py` | Non-destructive defaults, cleanup opt-in, and E2E suite ownership |
| `IMGBM_UT_149` | `test_catalog_validation.py` | Image Thrillhouse v0.0.26 alignment across x86_64/AArch64 runtime pins and every bundled catalog |
| `IMGBM_UT_150`–`151` | `test_registry_version_contract.py` | Registry 3.1.2 pin alignment across deploy/cleanup and active-service reconciliation |

The runner resolves each ID from the test file, class, and method portion of
the pytest node ID and displays it in the summary and generated reports.
Parameterized variants of one method intentionally share that method's ID.
Every mapping stores its ID explicitly, so source reordering cannot renumber
published cases. Append new mappings with the next available ID.

The input-contract cases model the runtime flow explicitly:

- `--tags validate` validates image-build configuration, credentials,
  package groups, and catalog input without requiring `repo_status.yml`.
- Build, execute, architecture-specific, and default build flows validate
  `repo_status.yml` before parsing it.
- Only `overall_status`, `cluster_os_type`, and `repositories` are required
  from `repo_status.yml`; Repo Manager metadata is validated only when a
  consumed optional value is present.

## Execution

Run the complete suite from `test/image_build_manager/`:

```bash
./run_validation.sh ut_image_build_manager test
```

Run only the catalog/runtime version contract with:

```bash
python3 -m pytest ut/test_catalog_validation.py -q \
  -k all_catalogs_match_thrillhouse_runtime_version
```
