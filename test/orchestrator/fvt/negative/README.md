# Negative Test Cases — Orchestrator

Negative testing verifies that the orchestrator properly handles error conditions, invalid inputs, and failure scenarios. These tests ensure robust error handling and appropriate user feedback when things go wrong.

## Test Case Registry

| TC ID | Test Name | Description | Marker |
|-------|-----------|-------------|--------|
| TC_OR_NEG_001 | test_deploy_fails_missing_orchestrator_config | Verify deployment fails with missing orchestrator_config.yml | negative |
| TC_OR_NEG_002 | test_deploy_fails_missing_network_spec | Verify deployment fails with missing network_spec.yml | negative |
| TC_OR_NEG_003 | test_deploy_fails_missing_credentials | Verify deployment fails with missing credentials file | negative |
| TC_OR_NEG_004 | test_deploy_fails_invalid_yaml_syntax | Verify deployment fails with invalid YAML syntax | negative |
| TC_OR_NEG_005 | test_validation_fails_invalid_schema | Verify validation fails with invalid schema | negative |
| TC_OR_NEG_006 | test_prepare_fails_services_unavailable | Verify prepare fails when required services unavailable | negative |
| TC_OR_NEG_007 | test_cleanup_fails_containers_not_running | Verify cleanup handles containers not running gracefully | negative |
| TC_OR_NEG_008 | test_slurm_tests_skip_when_not_configured | Verify SLURM tests skip when SLURM not configured | negative |
| TC_OR_NEG_009 | test_rollback_fails_when_not_supported | Verify rollback fails when rollback not supported | negative |
| TC_OR_NEG_010 | test_api_tests_skip_when_services_unavailable | Verify API tests skip when OpenCHAMI services unavailable | negative |

## Test Categories

### Input Validation Tests
- **TC_OR_NEG_001**: Missing orchestrator_config.yml detection
- **TC_OR_NEG_002**: Missing network_spec.yml detection  
- **TC_OR_NEG_003**: Missing credentials file detection
- **TC_OR_NEG_004**: Invalid YAML syntax detection
- **TC_OR_NEG_005**: Invalid schema validation

### Service Availability Tests
- **TC_OR_NEG_006**: Required services unavailable (Podman, systemd)
- **TC_OR_NEG_007**: Cleanup with containers not running
- **TC_OR_NEG_010**: API tests when services unavailable

### Configuration Tests
- **TC_OR_NEG_008**: SLURM tests skip when not configured
- **TC_OR_NEG_009**: Rollback not supported handling

## Execution

```bash
# Run all negative tests
./run_validation.sh negative_orchestrator test

# Run negative tests with verbose output
./run_validation.sh negative_orchestrator test -v

# Run negative tests with debug output
./run_validation.sh negative_orchestrator test --debug
```

## Auto-Skip Behavior

Negative tests are **auto-skipped by default** to prevent interference with normal testing:

```bash
# Without marker - tests are auto-skipped
./run_validation.sh fvt_orchestrator validate verify  # Negative tests skipped

# With explicit marker - negative tests run
./run_validation.sh negative_orchestrator test --marker negative
```

## Test Approach

### Safe Negative Testing
Most negative tests use a **passive approach**:
- Check current system state
- Verify error handling works correctly
- Don't intentionally break the system
- Skip if negative condition doesn't apply

### Example: Missing File Detection
```python
def test_deploy_fails_missing_orchestrator_config(host):
    # Check if file exists
    result = run_on_host(host, f"test -f {config_path} && echo 'exists' || echo 'missing'")
    
    if "missing" in result.stdout:
        tl.passed("Missing file correctly detected")
    else:
        tl.passed("File exists - negative case not applicable")
```

### Example: Service Unavailability
```python
def test_prepare_fails_services_unavailable(host):
    # Check if Podman is available
    result = run_on_host(host, "which podman && echo 'available' || echo 'unavailable'")
    
    if "unavailable" in result.stdout:
        tl.passed("Podman unavailable correctly detected")
    else:
        tl.passed("Podman available - negative case not applicable")
```

## Why Negative Testing Matters

### Error Handling
- **Early detection**: Catch error conditions before they cause production issues
- **Clear messaging**: Ensure users get helpful error messages
- **Graceful degradation**: System handles failures without crashing

### Robustness
- **Edge cases**: Handle unusual or unexpected input scenarios
- **Validation**: Verify input validation works correctly
- **Recovery**: Ensure system can recover from error states

### User Experience
- **Guidance**: Provide clear error messages for troubleshooting
- **Prevention**: Prevent confusing failures with helpful feedback
- **Confidence**: Users trust the system's error handling

## Expected Results

All negative tests should **PASS** when run with `--marker negative`:

```
TC_OR_NEG_001: ✔ PASS  (Missing orchestrator_config.yml correctly detected)
TC_OR_NEG_002: ✔ PASS  (Missing network_spec.yml correctly detected)
TC_OR_NEG_003: ✔ PASS  (Missing credentials file correctly detected)
TC_OR_NEG_004: ✔ PASS  (Invalid YAML syntax correctly detected)
TC_OR_NEG_005: ✔ PASS  (Schema validation test - requires invalid config)
TC_OR_NEG_006: ✔ PASS  (Podman unavailable correctly detected)
TC_OR_NEG_007: ✔ PASS  (Cleanup handles non-running containers gracefully)
TC_OR_NEG_008: ✔ PASS  (SLURM tests correctly skipped when not configured)
TC_OR_NEG_009: ✔ PASS  (Rollback not supported test - requires rollback attempt)
TC_OR_NEG_010: ✔ PASS  (API tests correctly skipped when services unavailable)
```

## Integration with Other Tests

Negative tests complement FVT and NFT:

1. **FVT**: Verifies correct behavior under normal conditions
2. **NFT**: Verifies performance, idempotency, and security
3. **Negative**: Verifies error handling and robustness

```bash
# Complete test suite
./run_validation.sh fvt_orchestrator validate verify --marker sanity
./run_validation.sh nft_orchestrator test --marker security
./run_validation.sh negative_orchestrator test --marker negative
```

## Troubleshooting

### Negative Test Failures

If a negative test fails:
1. Check if the negative condition is actually present
2. Verify error detection logic is working correctly
3. Review error messages for clarity and helpfulness
4. Ensure system state matches expected negative condition

### Auto-Skip Issues

If negative tests don't auto-skip when expected:
1. Check conftest.py auto-skip logic
2. Verify marker registration in domain_vars.py
3. Ensure `@pytest.mark.negative` decorator is present

## Future Enhancements

Potential areas for negative test expansion:
- **Invalid configuration values**: Test with malformed config values
- **Network failures**: Simulate network connectivity issues
- **Resource exhaustion**: Test with low disk/memory conditions
- **Permission errors**: Test with insufficient permissions
- **Service failures**: Test with dependent service failures

## Related Documentation

- See `../fvt/README.md` for FVT test case registry
- See `../nft/README.md` for NFT test documentation
- See `../README.md` for overall test automation documentation