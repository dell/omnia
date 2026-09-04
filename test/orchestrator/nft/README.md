# Non-Functional Tests (NFT) — Orchestrator

Non-Functional Tests validate **performance**, **idempotency**, and **security** of the orchestrator playbooks. Unlike FVT (which verifies correctness), NFT ensures that operations complete within acceptable timeframes, produce consistent results across repeated executions, and maintain proper security configurations.

---

## Test Categories

| Category | Description | Marker |
|----------|-------------|--------|
| Performance | Verify playbooks complete within time thresholds | performance |
| Idempotency | Verify playbooks can run multiple times safely | idempotency |
| Security | Verify file permissions and encryption | security |

## Test Case Registry

### Performance Tests

| TC ID | Test | Threshold | Marker |
|-------|------|-----------|--------|
| NFT_OR_001 | Validate performance | < 30s | nft, performance |
| NFT_OR_002 | Prepare performance | < 300s (5 min) | nft, performance |
| NFT_OR_003 | Provision performance | < 1800s (30 min) | nft, performance |
| NFT_OR_004 | Cleanup performance | < 180s (3 min) | nft, performance |

**Performance thresholds** ensure that orchestrator operations complete in reasonable timeframes:
- **Validate**: Configuration validation should be fast (< 30 seconds)
- **Prepare**: OpenCHAMI deployment should complete in under 5 minutes
- **Provision**: Full node provisioning should complete in under 30 minutes
- **Cleanup**: Container/service cleanup should complete in under 3 minutes

### Idempotency Tests

| TC ID | Test | Marker |
|-------|------|--------|
| NFT_OR_005 | Prepare idempotency (OpenCHAMI containers stable) | nft, idempotency |
| NFT_OR_006 | Validate idempotency (config validation safe to re-run) | nft, idempotency |
| NFT_OR_007 | Cleanup idempotency (safe to cleanup twice) | nft, idempotency |

**Idempotency tests** verify that playbooks can be run multiple times without errors:
- **Prepare idempotency**: Running prepare twice should succeed and keep OpenCHAMI containers stable
- **Validate idempotency**: Running validate twice should succeed without errors
- **Cleanup idempotency**: Running cleanup twice should succeed and keep resources cleaned

### Security Tests

| TC ID | Test | Marker |
|-------|------|--------|
| NFT_OR_008 | Credential file permissions (0640 or stricter) | nft, security |
| NFT_OR_009 | SSH key permissions (0600) | nft, security |
| NFT_OR_010 | Sensitive log file permissions | nft, security |
| NFT_OR_011 | Ansible vault encryption verification | nft, security |

**Security tests** verify that sensitive files have proper access controls:
- **Credential permissions**: Ensure credential files are not world-readable
- **SSH key permissions**: Ensure SSH private keys have owner-only access
- **Log file permissions**: Ensure log files don't expose sensitive information
- **Vault encryption**: Verify Ansible vault encryption is properly configured

## Execution

```bash
# Run all NFT tests
./run_validation.sh nft_orchestrator test

# Run only performance tests
./run_validation.sh nft_orchestrator test --marker performance

# Run only idempotency tests
./run_validation.sh nft_orchestrator test --marker idempotency

# Run only security tests
./run_validation.sh nft_orchestrator test --marker security

# Run with verbose output
./run_validation.sh nft_orchestrator test -v

# Run with debug output
./run_validation.sh nft_orchestrator test --debug
```

## Test Flow

### Performance Test Flow

```
1. NFT_OR_001: Run validate playbook, measure duration
   ├─ Assert: rc=0 (playbook succeeded)
   └─ Assert: duration < 30s

2. NFT_OR_002: Run prepare playbook, measure duration
   ├─ Assert: rc=0 (playbook succeeded)
   └─ Assert: duration < 300s

3. NFT_OR_003: Run provision playbook, measure duration
   ├─ Assert: rc=0 (playbook succeeded)
   └─ Assert: duration < 1800s

4. NFT_OR_004: Run cleanup playbook, measure duration
   ├─ Assert: rc=0 (playbook succeeded)
   └─ Assert: duration < 180s
```

### Idempotency Test Flow

```
1. NFT_OR_005: Prepare idempotency
   ├─ Run 1: Prepare playbook (initial deployment)
   ├─ Run 2: Prepare playbook (idempotent re-run)
   └─ Assert: Both runs exit 0, containers stable

2. NFT_OR_006: Validate idempotency
   ├─ Run 1: Validate playbook (initial validation)
   ├─ Run 2: Validate playbook (idempotent re-run)
   └─ Assert: Both runs exit 0

3. NFT_OR_007: Cleanup idempotency
   ├─ Run 1: Cleanup playbook (initial cleanup)
   ├─ Run 2: Cleanup playbook (idempotent re-run)
   └─ Assert: Both runs exit 0, resources remain cleaned
```

### Security Test Flow

```
1. NFT_OR_008: Credential file permissions
   └─ Assert: omnia_config_credentials.yml has 0640 or stricter

2. NFT_OR_009: SSH key permissions
   └─ Assert: SSH private keys have 0600 permissions

3. NFT_OR_010: Sensitive log file permissions
   └─ Assert: Log files are not world-readable

4. NFT_OR_011: Vault encryption verification
   └─ Assert: Vault header present, key file has 0600
```

## Why NFT Matters

### Performance Testing
- **Early detection**: Catch performance regressions before production
- **Capacity planning**: Understand resource requirements and timing
- **User experience**: Ensure operations complete in acceptable timeframes
- **SLA compliance**: Verify service level agreements are met

### Idempotency Testing
- **Reliability**: Playbooks must be safe to run multiple times
- **Error recovery**: Users can re-run after failures without manual cleanup
- **CI/CD safety**: Automated pipelines can safely retry operations
- **Operational efficiency**: Reduce manual intervention in production

### Security Testing
- **Data protection**: Ensure sensitive files are properly protected
- **Compliance**: Meet security standards and regulatory requirements
- **Audit readiness**: Maintain proper access controls
- **Risk mitigation**: Reduce security vulnerabilities

## Expected Results

All NFT tests should **PASS** on a healthy orchestrator deployment:

```
NFT_OR_001: ✔ PASS  (validate: 12.3s < 30s)
NFT_OR_002: ✔ PASS  (prepare: 245.7s < 300s)
NFT_OR_003: ✔ PASS  (provision: 1542.1s < 1800s)
NFT_OR_004: ✔ PASS  (cleanup: 125.4s < 180s)
NFT_OR_005: ✔ PASS  (prepare idempotent: run1=245.7s, run2=3.2s)
NFT_OR_006: ✔ PASS  (validate idempotent: run1=12.3s, run2=11.8s)
NFT_OR_007: ✔ PASS  (cleanup idempotent: run1=125.4s, run2=2.1s)
NFT_OR_008: ✔ PASS  (credential file permissions: 0640)
NFT_OR_009: ✔ PASS  (SSH key permissions: 0600)
NFT_OR_010: ✔ PASS  (log file permissions: no world-readable)
NFT_OR_011: ✔ PASS  (vault encryption: header present, key 0600)
```

## Troubleshooting

### Performance Test Failures

If a performance test fails:
1. Check if the playbook succeeded (rc=0) but was slow
2. Review cluster resource availability (CPU, memory, network)
3. Check for external dependencies (image registry, DNS, storage)
4. Consider adjusting thresholds if infrastructure is slower
5. Review orchestrator logs for bottlenecks

### Idempotency Test Failures

If an idempotency test fails:
1. Check the second run's exit code and error messages
2. Look for tasks that fail when resources already exist
3. Verify tasks use proper guards:
   - `changed_when: false` for check commands
   - `failed_when: false` for cleanup commands
   - `--ignore-not-found=true` for kubectl delete
   - Proper Ansible idempotency patterns
4. Review playbook logic for conditional task execution

### Security Test Failures

If a security test fails:
1. Check current file permissions using `stat` or `ls -l`
2. Verify file ownership and group membership
3. Update file permissions using `chmod`
4. Review Ansible vault configuration
5. Ensure vault key files are properly protected

## Adjusting Thresholds

Edit the constants in `nft/test_performance.py`:

```python
VALIDATE_THRESHOLD = 30     # 30 seconds
PREPARE_THRESHOLD = 300     # 5 minutes
PROVISION_THRESHOLD = 1800  # 30 minutes
CLEANUP_THRESHOLD = 180     # 3 minutes
```

For faster hardware, reduce thresholds. For CI/CD pipelines with shared resources, consider increasing them. Document any threshold changes with rationale.

## Prerequisites

Run these commands from `test/orchestrator/`. NFT requires a valid target environment, input configuration, and credentials:

```bash
# Validate prerequisites
./run_validation.sh fvt_orchestrator validate verify

# Run NFT (includes cleanup operations)
./run_validation.sh nft_orchestrator test
```

**Note**: NFT tests execute actual playbook operations including cleanup. Ensure you have proper backups and understand the impact before running NFT in production environments.

## Integration with FVT

NFT complements FVT by testing non-functional aspects:

1. **Run FVT first** to verify functional correctness
2. **Run NFT** to verify performance, idempotency, and security
3. **Use both** for comprehensive testing coverage

```bash
# Complete test suite
./run_validation.sh fvt_orchestrator validate verify
./run_validation.sh fvt_orchestrator prepare verify
./run_validation.sh nft_orchestrator test
```

## Related Documentation

- See `../fvt/README.md` for FVT test case registry
- See `../README.md` for overall test automation documentation
- See `../docs/` for detailed configuration documentation