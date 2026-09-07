# Telemetry — NFT Test Cases

Non-Functional Tests (NFT) for telemetry playbook performance and idempotency.

## Test Categories

| Category | Description | Marker |
|----------|-------------|--------|
| Performance | Verify playbooks complete within time thresholds | performance |
| Idempotency | Verify playbooks can run multiple times safely | idempotency |

## Test Case Registry

### Performance Tests

| TC ID | Test | Threshold | Marker |
|-------|------|-----------|--------|
| NFT_TL_001 | Validate performance | < 30s | nft, performance |
| NFT_TL_002 | Deploy performance | < 600s (10 min) | nft, performance |
| NFT_TL_003 | Cleanup performance | < 300s (5 min) | nft, performance |

**Performance thresholds** ensure that telemetry operations complete in
reasonable timeframes:
- **Validate**: Configuration validation should be fast (< 30 seconds)
- **Deploy**: Full stack deployment (sinks + sources) should complete in under 10 minutes
- **Cleanup**: Full cleanup should complete in under 5 minutes

### Idempotency Tests

| TC ID | Test | Marker | Condition |
|-------|------|--------|-----------|
| NFT_TL_004 | Deploy idempotency (second run exits 0) | nft, idempotency | always |
| NFT_TL_005 | Cleanup idempotency (second run exits 0) | nft, idempotency | always |
| TC_CL_011-idem | Verify no pods after idempotent cleanup | nft, idempotency | always |
| TC_CL_012-idem | Verify no PVCs after idempotent cleanup | nft, idempotency | `DELETE_VOLUME=true` |
| TC_CL_013-idem | Verify PVCs preserved after idempotent cleanup | nft, idempotency | `DELETE_VOLUME` unset/`false` (default) |

**Idempotency tests** verify that playbooks can be run multiple times
without errors:
- **Deploy idempotency**: Running deploy twice should succeed (rc=0) both times
- **Cleanup idempotency**: Running cleanup twice should succeed (rc=0) both times.
  Both runs use the same `Delete_volume` value, resolved from the
  `DELETE_VOLUME` environment variable (default: `false`).
- **Resource verification**: After idempotent cleanup, pods are always
  gone; PVCs are deleted only when `DELETE_VOLUME=true`, otherwise they
  must be preserved.

## Execution

```bash
# Run all NFT tests
./run_validation.sh nft_telemetry test

# Run only performance tests
./run_validation.sh nft_telemetry test --marker performance

# Run only idempotency tests
./run_validation.sh nft_telemetry test --marker idempotency

# Run with verbose output
./run_validation.sh nft_telemetry test -v

# Run with debug output
./run_validation.sh nft_telemetry test --debug

# Idempotency with PVC deletion (Delete_volume=true both runs)
DELETE_VOLUME=true ./run_validation.sh nft_telemetry test --marker idempotency
```

## Test Flow

### Performance Test Flow

```
1. NFT_TL_001: Run validate playbook, measure duration
   ├─ Assert: rc=0 (playbook succeeded)
   └─ Assert: duration < 30s

2. NFT_TL_002: Run deploy playbook, measure duration
   ├─ Assert: rc=0 (playbook succeeded)
   └─ Assert: duration < 600s

3. NFT_TL_003: Run cleanup playbook, measure duration
   ├─ Assert: rc=0 (playbook succeeded)
   └─ Assert: duration < 300s
```

### Idempotency Test Flow

```
1. NFT_TL_004: Deploy idempotency
   ├─ Run 1: Deploy playbook (initial deployment)
   ├─ Run 2: Deploy playbook (idempotent re-run)
   └─ Assert: Both runs exit 0

2. NFT_TL_005: Cleanup idempotency
   ├─ Run 1: Cleanup playbook (initial cleanup; -e Delete_volume=true if DELETE_VOLUME=true)
   ├─ Run 2: Cleanup playbook (idempotent re-run; same Delete_volume value)
   └─ Assert: Both runs exit 0

3. TC_CL_011-idem: Verify no pods remain
   └─ Assert: kubectl get pods -n telemetry returns 0 pods

4a. TC_CL_012-idem (DELETE_VOLUME=true): Verify no PVCs remain
    └─ Assert: kubectl get pvc -n telemetry returns 0 PVCs

4b. TC_CL_013-idem (DELETE_VOLUME unset/false, default): Verify PVCs preserved
    └─ Assert: kubectl get pvc -n telemetry returns > 0 PVCs
```

## Why NFT Matters

### Performance Testing
- **Early detection**: Catch performance regressions before production
- **Capacity planning**: Understand resource requirements and timing
- **User experience**: Ensure operations complete in acceptable timeframes

### Idempotency Testing
- **Reliability**: Playbooks must be safe to run multiple times
- **Error recovery**: Users can re-run after failures without manual cleanup
- **CI/CD safety**: Automated pipelines can safely retry operations

## Expected Results

All NFT tests should **PASS** on a healthy telemetry deployment:

```
NFT_TL_001: ✔ PASS  (validate: 12.3s < 30s)
NFT_TL_002: ✔ PASS  (deploy: 487.2s < 600s)
NFT_TL_003: ✔ PASS  (cleanup: 125.4s < 300s)
NFT_TL_004: ✔ PASS  (deploy idempotent: run1=0, run2=0)
NFT_TL_005: ✔ PASS  (cleanup idempotent: run1=0, run2=0)
TC_CL_011-idem: ✔ PASS  (0 pods remaining)
TC_CL_013-idem: ✔ PASS  (PVCs preserved, DELETE_VOLUME unset/false)
```

With `DELETE_VOLUME=true`, `TC_CL_012-idem` runs (and asserts 0 PVCs)
instead of `TC_CL_013-idem`:

```
TC_CL_012-idem: ✔ PASS  (0 PVCs remaining, DELETE_VOLUME=true)
```

## Troubleshooting

### Performance Test Failures

If a performance test fails:
1. Check if the playbook succeeded (rc=0) but was slow
2. Review cluster resource availability (CPU, memory, network)
3. Check for external dependencies (image registry, DNS, storage)
4. Consider adjusting thresholds if infrastructure is slower

### Idempotency Test Failures

If an idempotency test fails:
1. Check the second run's exit code and error messages
2. Look for tasks that fail when resources already exist
3. Verify tasks use proper guards:
   - `changed_when: false` for check commands
   - `failed_when: false` for cleanup commands
   - `--ignore-not-found=true` for kubectl delete
   - Helm guards for already-uninstalled releases

## Related Documentation

- See `../fvt/README.md` for FVT test case registry
- See `../README.md` for overall test automation documentation
