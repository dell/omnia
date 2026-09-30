# Skip Reasons Implementation for repo_manager FVT

## Overview
Updated all skipped tests in the repo_manager FVT framework to display skip reasons in the same format as `image_build_manager`, using `TestLogger.skipped_fields()` before calling `pytest.skip()`.

## Format Pattern
Following the image_build_manager pattern:

```python
tl.skipped_fields(
    "Main skip reason message",
    {
        "Field 1": "value1",
        "Field 2": "value2",
        "Field 3": "value3",
    }
)
pytest.skip("pytest skip message")
```

This produces output like:
```
▶ [TEST_ID] Test description
↷ SKIP: Main skip reason message
  │ Field 1: value1
  │ Field 2: value2
  │ Field 3: value3
```

## Files Modified

### 1. Policy Tests (execute/policy/)

#### test_policy_combinations.py
- **test_policy_always_caching_false** (V007): Shows configured repos count, required policy/caching, expected Pulp mode
- **test_policy_always_caching_true** (V008): Shows configured repos count, required policy/caching, expected Pulp mode
- **test_policy_partial_caching_false** (V009): Shows configured repos count, required policy/caching, expected Pulp mode
- **test_policy_partial_caching_true** (V010): Shows configured repos count, required policy/caching, expected Pulp mode

#### test_partial_override.py
- **test_per_repo_policy_only** (V004): Shows configured repos count, policy/caching sources
- **test_per_repo_caching_only** (V005): Shows configured repos count, policy/caching sources

#### test_priority_order.py
- **test_per_repo_policy_overrides_global** (V001): Shows configured repos count, per-repo overrides count, policy source
- **test_per_repo_caching_overrides_global** (V002): Shows configured repos count, per-repo overrides count, caching source
- **test_per_repo_complete_override** (V003): Shows configured repos count, complete overrides count, policy/caching sources

#### test_repo_types.py
- **test_subscription_repo_per_repo_override** (V011): Shows deployed repos count, repository type, per-repo overrides count

### 2. Negative Tests

#### execute/negative/test_negative.py
- **test_download_fails_invalid_repo_url** (NEG_003): Shows test type, requirement, purpose
- **test_repo_sync_fails_network_issues** (NEG_007): Shows test type, requirement, purpose
- **test_catalog_generation_fails_invalid_config** (NEG_008): Shows test type, requirement, purpose

#### precheck/negative/test_negative.py
- **test_deploy_fails_missing_credentials** (NEG_001): Shows test type, requirement, purpose
- **test_deploy_fails_invalid_endpoint_config** (NEG_002): Shows test type, requirement, purpose
- **test_validate_fails_missing_config** (NEG_009): Shows config file, status, test type

### 3. Optional Repository Tests (execute/repos/)

#### test_repos.py
- **test_slurm_custom_repo_present** (V003): Shows repository name, architecture, configuration file
- **test_epel_repo_present** (V004): Shows repository name, architecture, configuration file
- **test_x86_64_repos_present** (V005): Shows repository names, architecture, configuration file
- **test_file_repos_present** (V006): Shows repository name, architecture, configuration file

## Skip Reason Categories

### 1. Policy Configuration Not Present
When a specific policy/caching combination is not configured in the deployment:
```
↷ SKIP: No repo with always+false configuration found
  │ Configured repos: 8
  │ Required policy: always
  │ Required caching: false
  │ Expected Pulp mode: immediate
```

### 2. Negative Tests (Intentionally Skipped)
When negative tests are skipped to avoid interference:
```
↷ SKIP: Negative test - skipped in normal verification
  │ Test type: negative
  │ Requirement: config modification
  │ Purpose: simulate invalid repository URL
```

### 3. Optional Repositories Not Configured
When optional repositories are not configured:
```
↷ SKIP: Optional repository not configured
  │ Repository: slurm_custom
  │ Architecture: x86_64
  │ Configuration file: repo_manager_config.yml
```

### 4. Configuration Present (Negative Test Not Applicable)
When negative test conditions are not met:
```
↷ SKIP: Configuration present - test not applicable
  │ Config file: repo_manager_config.yml
  │ Status: exists
  │ Test type: negative
```

## Benefits

1. **Consistency**: All skipped tests now use the same format as image_build_manager
2. **Clarity**: Skip reasons are clearly displayed with structured details
3. **Debugging**: Users can quickly understand why a test was skipped
4. **Maintainability**: Centralized skip reason logic using TestLogger

## Example Output

```
▶ [RM_FVT_POLICY_V007] policy: always + caching: false = immediate
↷ SKIP: No repo with always+false configuration found
  │ Configured repos: 8
  │ Required policy: always
  │ Required caching: false
  │ Expected Pulp mode: immediate
.

▶ [RM_FVT_NEG_003] Download fails with invalid repository URL
↷ SKIP: Negative test - skipped in normal verification
  │ Test type: negative
  │ Requirement: config modification
  │ Purpose: simulate invalid repository URL
.

▶ [RM_FVT_EXECUTE_V003] Verify slurm_custom repo present
↷ SKIP: Optional repository not configured
  │ Repository: slurm_custom
  │ Architecture: x86_64
  │ Configuration file: repo_manager_config.yml
.
```

## Total Tests Updated

- **Policy tests**: 7 tests
- **Negative tests**: 5 tests
- **Optional repo tests**: 4 tests
- **Total**: 16 tests with improved skip reason formatting
