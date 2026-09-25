# Telemetry -- NFT Test Cases

Non-Functional Tests (NFT) for telemetry playbook performance, idempotency,
and resilience.

NFT IDs use `TEL_NFT_<SEQ>`: `TEL` is the stable Telemetry domain code, `NFT`
identifies the test level, and `SEQ` is a stable three-digit sequence.

## Test Categories

| Category | Description | Marker |
|----------|-------------|--------|
| Performance | Verify playbooks complete within time thresholds | performance |
| Idempotency | Verify playbooks can run multiple times safely | idempotency |
| Resilience | Verify recovery from pod deletion, node reboot, and lifecycle | resilience |

## Test Case Registry

### Performance Tests

| TC ID | Test | Threshold | Calculation | Order | Marker |
|-------|------|-----------|-------------|-------|--------|
| TEL_NFT_001 | Validate performance | < 45s | 30s + 50% buffer | 100 | nft, performance |
| TEL_NFT_002 | Deploy performance | < 800s (13.3 min) | 60s (prereq) + 400s (sinks) + 200s (sources) + 60s (verify) + 20% buffer | 101 | nft, performance |
| TEL_NFT_003 | Cleanup performance (without volume) | < 360s (6 min) | 200s (cleanup) + 60s (verify) + 20% buffer | 130 | nft, performance |
| TEL_NFT_020 | Cleanup with volume deletion performance | < 360s (6 min) | Same as Phase 1 (volume deletion is async) | 140 | nft, performance |

**Threshold Rationale:**
- **Validate (45s)**: Fast operation with 50% buffer for config parsing and validation
- **Deploy (800s)**: Full stack with all 6 sources (iDRAC, LDMS, PowerScale, UFM, VAST, OME) + 20% infrastructure buffer
- **Cleanup (360s)**: All sources + sinks cleanup + 20% buffer (volume deletion doesn't increase time significantly)

### Idempotency Tests

| TC ID | Test | Order | Phase | Marker |
|-------|------|-------|-------|--------|
| TEL_NFT_004 | Deploy idempotency (second run exits 0) | 105 | Pre-cleanup | nft, idempotency |
| TEL_NFT_005 | Cleanup idempotency without volume (second run exits 0) | 131 | Phase 1 | nft, idempotency |
| TEL_NFT_015 | Verify no pods after cleanup | 132 | Phase 1 | nft, idempotency |
| TEL_NFT_017 | Verify PVCs preserved after cleanup | 133 | Phase 1 | nft, idempotency |
| TEL_NFT_021 | Cleanup with volume idempotency (second run exits 0) | 141 | Phase 2 | nft, idempotency |
| TEL_NFT_022 | Verify no pods after cleanup with volume | 142 | Phase 2 | nft, idempotency |
| TEL_NFT_016 | Verify no PVCs after cleanup with volume | 143 | Phase 2 | nft, idempotency |

**Cleanup test execution is split into two phases:**
- **Phase 1** (orders 130-133): Cleanup WITHOUT volume deletion — PVCs are preserved
- **Phase 2** (orders 140-143): Cleanup WITH volume deletion — all PVCs are deleted

This ensures each verification test runs immediately after its corresponding
cleanup phase, producing correct results.

### Resilience Tests

| TC ID | Test | Recovery Timeout | Marker |
|-------|------|-----------------|--------|
| TEL_NFT_006 | Sink pod deletion & recovery (Kafka broker) | 300s | nft, resilience |
| TEL_NFT_007 | Source pod deletion & recovery (enabled sources) | 300s | nft, resilience |
| TEL_NFT_008 | StatefulSet storage pod recovery (vmstorage/vlstorage) | 600s | nft, resilience |
| TEL_NFT_009 | PVC persistence after pod deletion | N/A | nft, resilience |
| TEL_NFT_010 | Service endpoint availability after pod restart | N/A | nft, resilience |
| TEL_NFT_011 | Data ingestion after sink restart | N/A | nft, resilience |
| TEL_NFT_012 | Node reboot recovery (all pods Running) | 600s | nft, resilience |
| TEL_NFT_013 | Full lifecycle (cleanup -> redeploy -> verify) | 720s | nft, resilience |
| TEL_NFT_014 | Operator pod recovery (VM/Strimzi operators) | 300s | nft, resilience |

**Resilience tests** verify the telemetry stack's ability to recover:
- **Pod deletion**: K8s controllers (Deployments/StatefulSets) must recreate deleted pods
- **PVC persistence**: Persistent volume data must survive pod restarts
- **Service endpoints**: Services must regain active endpoints after pod recreation
- **Data continuity**: VictoriaMetrics must retain queryable data after storage pod restart
- **Node reboot**: All pods must return to Running state after node reboot
- **Full lifecycle**: Complete cleanup and redeployment must produce a healthy stack
- **Operator recovery**: Operator pods must be recreated and CRs must reconcile.
  VMCluster health is verified via `.status.updateStatus` (expected: `operational`);
  Kafka health via `.status.conditions[Ready].status` (expected: `True`).

## Execution

### Full NFT Test Suite (Recommended)

```bash
# Run all NFT tests (includes both DELETE_SINKS_VOLUME=false and DELETE_SINKS_VOLUME=true scenarios)
# This is the comprehensive test run that validates all cleanup modes in a single execution
./run_validation.sh nft_telemetry test
```

**What this executes (in order):**

| Order | TC ID | Phase | Description |
|-------|-------|-------|-------------|
| 100 | TEL_NFT_001 | Pre-cleanup | Validate performance |
| 101 | TEL_NFT_002 | Pre-cleanup | Deploy performance |
| 105 | TEL_NFT_004 | Pre-cleanup | Deploy idempotency |
| 110 | TEL_NFT_018 | Resilience | Resilience setup deploy |
| 111-120 | TEL_NFT_006-014 | Resilience | Pod recovery, node reboot, lifecycle, operator tests |
| 130 | TEL_NFT_003 | Phase 1 | Cleanup performance (PVCs preserved) |
| 131 | TEL_NFT_005 | Phase 1 | Cleanup idempotency (PVCs preserved) |
| 132 | TEL_NFT_015 | Phase 1 | Verify no pods after cleanup |
| 133 | TEL_NFT_017 | Phase 1 | Verify PVCs preserved |
| 140 | TEL_NFT_020 | Phase 2 | Cleanup with volume performance (PVCs deleted) |
| 141 | TEL_NFT_021 | Phase 2 | Cleanup with volume idempotency (PVCs deleted) |
| 142 | TEL_NFT_022 | Phase 2 | Verify no pods after cleanup with volume |
| 143 | TEL_NFT_016 | Phase 2 | Verify no PVCs remain |

This consolidated approach eliminates the need to run the NFT suite twice with different flags.

### Selective Test Execution

```bash
# Run only performance tests
./run_validation.sh nft_telemetry test --marker performance

# Run only idempotency tests
./run_validation.sh nft_telemetry test --marker idempotency

# Run only resilience tests
./run_validation.sh nft_telemetry test --marker resilience

# Run resilience + performance together
./run_validation.sh nft_telemetry test --marker resilience,performance

# Run with verbose output
./run_validation.sh nft_telemetry test -v

# Run with debug output
./run_validation.sh nft_telemetry test --debug
```

## Final Cluster State After NFT Execution

**CRITICAL**: After running the full NFT test suite (`./run_validation.sh nft_telemetry test`), the cluster is left in a **fully cleaned-up state** with:
- ❌ No telemetry pods running
- ❌ All PVCs deleted (including Kafka, VictoriaMetrics, VictoriaLogs)
- ❌ **Input files deleted** (`<OMNIA_DATA_PATH>/telemetry/input/<OMNIA_PROJECT_NAME>/`)
- ❌ **Log files deleted** (`<OMNIA_DATA_PATH>/telemetry/log/`)
- ❌ **Credential files deleted** (`telemetry_credentials.yml`, `.telemetry_credentials_key`)

### Why Everything is Deleted

The consolidated NFT execution includes both test phases:
1. **Phase 1** (default): Tests with `DELETE_SINKS_VOLUME=false` — sink PVCs are preserved
2. **Phase 2** (final): Cleanup-with-volume deletion tests with `DELETE_SINKS_VOLUME=true` — **all PVCs, input files, logs, and credentials are deleted**

This ensures comprehensive coverage of both cleanup modes in a single run. The final cleanup phase (Phase 2) performs a complete cleanup with volume deletion, removing all data and configuration files.

### Before Running NFT: Backup Important Data

If you need to preserve any of the following, **take backups BEFORE running NFT**:
- **Input configuration files**: `<OMNIA_DATA_PATH>/telemetry/input/<OMNIA_PROJECT_NAME>/`
  - `telemetry_config.yml`
  - `telemetry_storage_config.yml`
  - `telemetry_packages.yml`
- **Historical logs**: `<OMNIA_DATA_PATH>/telemetry/log/<OMNIA_PROJECT_NAME>/`
- **Credentials**: `<OMNIA_DATA_PATH>/telemetry/input/<OMNIA_PROJECT_NAME>/`
  - `telemetry_credentials.yml`
  - `.telemetry_credentials_key`

### After NFT Completion: Restore Telemetry

To redeploy telemetry after NFT completion:

```bash
# 1. Restore input files from backup (if needed)
cp -r /path/to/backup/input/* <OMNIA_DATA_PATH>/telemetry/input/<OMNIA_PROJECT_NAME>/

# 2. Redeploy telemetry stack
ansible-playbook telemetry.yml --tags execute
```

**Note**: If you did not back up input files, you must restore them from the source domain directory before running deploy:
```bash
cp -r src/telemetry/input/* <OMNIA_DATA_PATH>/telemetry/input/<OMNIA_PROJECT_NAME>/
```

## Test Flow

### Performance Test Flow

```
1. TEL_NFT_001: Run validate playbook, measure duration
   |-- Assert: rc=0 (playbook succeeded)
   +-- Assert: duration < 30s

2. TEL_NFT_002: Run deploy playbook, measure duration
   |-- Assert: rc=0 (playbook succeeded)
   +-- Assert: duration < 600s

3. TEL_NFT_003: Run cleanup playbook (without volume), measure duration
   |-- Assert: rc=0 (playbook succeeded)
   +-- Assert: duration < 300s

4. TEL_NFT_020: Run cleanup playbook (with volume), measure duration
   |-- Assert: rc=0 (playbook succeeded)
   +-- Assert: duration < 300s
```

### Idempotency Test Flow

```
Phase 1: Cleanup WITHOUT volume deletion (PVCs preserved)
----------------------------------------------------------
1. TEL_NFT_004: Deploy idempotency
   |-- Run 1: Deploy playbook (initial deployment)
   |-- Run 2: Deploy playbook (idempotent re-run)
   +-- Assert: Both runs exit 0

2. TEL_NFT_005: Cleanup idempotency (without volume)
   |-- Run 1: Cleanup playbook (no Delete_sinks_volume)
   |-- Run 2: Cleanup playbook (idempotent re-run)
   +-- Assert: Both runs exit 0

3. TEL_NFT_015: Verify no pods remain
   +-- Assert: kubectl get pods -n telemetry returns 0 pods

4. TEL_NFT_017: Verify PVCs preserved
   +-- Assert: Source PVCs deleted, sink PVCs preserved

Phase 2: Cleanup WITH volume deletion (all PVCs deleted)
----------------------------------------------------------
5. TEL_NFT_021: Cleanup with volume idempotency
   |-- Run 1: Cleanup playbook (-e Delete_sinks_volume=true)
   |-- Run 2: Cleanup playbook (idempotent re-run)
   +-- Assert: Both runs exit 0

6. TEL_NFT_022: Verify no pods remain
   +-- Assert: kubectl get pods -n telemetry returns 0 pods

7. TEL_NFT_016: Verify no PVCs remain
   +-- Assert: kubectl get pvc -n telemetry returns 0 PVCs
```

### Resilience Test Flow

```
1. TEL_NFT_006: Sink pod deletion & recovery
   |-- Delete Kafka broker pods (force, grace-period=0)
   |-- Wait up to 300s for StatefulSet to recreate 3 broker pods
   +-- Assert: All 3 broker pods Running

2. TEL_NFT_007: Source pod deletion & recovery
   |-- Skip if no sources enabled
   |-- For each enabled source (iDRAC, Vector-LDMS, Vector-OME):
   |   |-- Delete pods by prefix
   |   +-- Wait for controller to recreate
   +-- Assert: All source pods recovered

3. TEL_NFT_008: StatefulSet storage pod recovery
   |-- Delete vmstorage pods (3 replicas)
   |-- Wait for STS to recreate with same identity
   |-- Delete vlstorage pods (3 replicas)
   |-- Wait for STS to recreate
   +-- Assert: All storage pods Running, re-attached to PVCs

4. TEL_NFT_009: PVC persistence after pod deletion
   |-- Query all PVCs in telemetry namespace
   +-- Assert: All PVCs in Bound state (data preserved)

5. TEL_NFT_010: Service endpoint availability
   |-- Check endpoints for kafka-kafka-bootstrap, vmselect,
   |   vminsert, vlselect
   +-- Assert: All services have active endpoints

6. TEL_NFT_011: Data ingestion after sink restart
   |-- Query VictoriaMetrics with 'up' metric
   +-- Assert: Results returned (data survived restart)

7. TEL_NFT_012: Node reboot recovery
   |-- Resolve kube_vip IP (skip if unavailable)
   |-- Reboot node via SSH
   |-- Wait for node to come back (600s timeout)
   |-- Wait for all telemetry pods to reach Running (600s timeout)
   +-- Assert: All pods Running after reboot

8. TEL_NFT_013: Full lifecycle
   |-- Run cleanup playbook (teardown, -e cleanup_credentials=false)
   |-- Run deploy playbook (redeploy, reuses preserved credentials)
   |-- Verify all pods Running
   +-- Assert: Complete cycle succeeds

9. TEL_NFT_014: Operator pod recovery
   |-- Delete victoria-metrics-operator pod
   |-- Wait for recreation, check VMCluster CR .status.updateStatus = operational
   |-- Delete strimzi-cluster-operator pod
   |-- Wait for recreation, check Kafka CR Ready condition = True
   +-- Assert: Both operators recovered, CRs reconciled
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

### Resilience Testing
- **Pod self-healing**: Kubernetes must automatically recover deleted pods
- **Data durability**: PVC-backed storage must survive pod restarts
- **Service continuity**: Service endpoints must recover after disruptions
- **Disaster recovery**: System must function after node reboots
- **Operational confidence**: Full lifecycle (tear down + rebuild) must work

## Expected Results

All NFT tests should **PASS** on a healthy telemetry deployment:

```
TEL_NFT_001: PASS  (validate: 12.3s < 45s)
TEL_NFT_002: PASS  (deploy: 633.8s < 800s)
TEL_NFT_004: PASS  (deploy idempotent: run1=0, run2=0)
TEL_NFT_018: PASS  (resilience setup deploy)
TEL_NFT_006: PASS  (kafka-broker: 3/3 recovered in 45s)
TEL_NFT_007: PASS  (idrac-telemetry: 1/1 recovered in 30s)
TEL_NFT_008: PASS  (vmstorage: 3/3, vlstorage: 3/3 recovered)
TEL_NFT_009: PASS  (18/18 PVCs Bound)
TEL_NFT_010: PASS  (4/4 services have endpoints)
TEL_NFT_011: PASS  (query 'up' returned 12 results)
TEL_NFT_012: PASS  (42 pods Running after node reboot in 180s)
TEL_NFT_013: PASS  (cleanup=125s, deploy=487s, 42 pods Running)
TEL_NFT_014: PASS  (VM operator: operational, Strimzi operator: True)
--- Phase 1: Cleanup without volume ---
TEL_NFT_003: PASS  (cleanup: 125.4s < 360s)
TEL_NFT_005: PASS  (cleanup idempotent: run1=0, run2=0)
TEL_NFT_015: PASS  (0 pods remaining)
TEL_NFT_017: PASS  (PVCs preserved)
--- Phase 2: Cleanup with volume ---
TEL_NFT_020: PASS  (cleanup with volume: 130.2s < 360s)
TEL_NFT_021: PASS  (cleanup with volume idempotent: run1=0, run2=0)
TEL_NFT_022: PASS  (0 pods remaining)
TEL_NFT_016: PASS  (0 PVCs remaining)
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

### Resilience Test Failures

If a resilience test fails:
1. **Pod recovery failures**: Check controller events
   - `kubectl describe sts <name> -n telemetry`
   - `kubectl describe deployment <name> -n telemetry`
   - Look for scheduling failures (insufficient resources, node affinity)
2. **PVC not Bound**: Check storage provisioner
   - `kubectl get pvc -n telemetry`
   - `kubectl get sc` (storage class availability)
3. **Service endpoint failures**: Check pod readiness probes
   - `kubectl get endpoints -n telemetry`
   - Pods must pass readiness checks before being added to endpoints
4. **Data queryability failures**: Check vmstorage + vmselect logs
   - `kubectl logs -n telemetry <vmstorage-pod>`
   - Verify PVC data integrity after restart
5. **Node reboot failures**: Check kubelet and container runtime
   - `systemctl status kubelet` on the rebooted node
   - `kubectl get nodes` for NotReady status
6. **Operator recovery failures**: Check operator logs and CR status
   - `kubectl logs -n telemetry <operator-pod>`
   - `kubectl get vmcluster -n telemetry` (STATUS should be `operational`)
   - `kubectl get kafka -n telemetry` (READY should be `True`)
   - Verify CRD versions are compatible with operator version
   - Note: VMCluster uses `.status.updateStatus` (not the deprecated
     `.status.clusterStatus` which was removed in VM operator v0.68.0)

## Related Documentation

- See `../fvt/README.md` for FVT test case registry
- See `../README.md` for overall test automation documentation
