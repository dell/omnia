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

| TC ID | Test | Threshold | Marker |
|-------|------|-----------|--------|
| TEL_NFT_001 | Validate performance | < 30s | nft, performance |
| TEL_NFT_002 | Deploy performance | < 600s (10 min) | nft, performance |
| TEL_NFT_003 | Cleanup performance | < 300s (5 min) | nft, performance |

**Performance thresholds** ensure that telemetry operations complete in
reasonable timeframes:
- **Validate**: Configuration validation should be fast (< 30 seconds)
- **Deploy**: Full stack deployment (sinks + sources) should complete in under 10 minutes
- **Cleanup**: Full cleanup should complete in under 5 minutes

### Idempotency Tests

| TC ID | Test | Marker | Condition |
|-------|------|--------|-----------|
| TEL_NFT_004 | Deploy idempotency (second run exits 0) | nft, idempotency | always |
| TEL_NFT_005 | Cleanup idempotency (second run exits 0) | nft, idempotency | always |
| TEL_NFT_015 | Verify no pods after idempotent cleanup | nft, idempotency | always |
| TEL_NFT_016 | Verify no PVCs after idempotent cleanup | nft, idempotency | `DELETE_VOLUME=true` |
| TEL_NFT_017 | Verify PVCs preserved after idempotent cleanup | nft, idempotency | `DELETE_VOLUME` unset/`false` (default) |

**Idempotency tests** verify that playbooks can be run multiple times
without errors:
- **Deploy idempotency**: Running deploy twice should succeed (rc=0) both times
- **Cleanup idempotency**: Running cleanup twice should succeed (rc=0) both times.
  Both runs use the same `Delete_volume` value, resolved from the
  `DELETE_VOLUME` environment variable (default: `false`).
- **Resource verification**: After idempotent cleanup, pods are always
  gone; PVCs are deleted only when `DELETE_VOLUME=true`, otherwise they
  must be preserved.

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

```bash
# Run all NFT tests
./run_validation.sh nft_telemetry test

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

# Idempotency with PVC deletion (Delete_volume=true both runs)
DELETE_VOLUME=true ./run_validation.sh nft_telemetry test --marker idempotency
```

## Final Cluster State After NFT Execution

**Important**: After running the full NFT test suite (`./run_validation.sh nft_telemetry test`), the cluster is left in a **cleaned-up state** with no telemetry pods running. The final state depends on the `DELETE_VOLUME` environment variable:

- **`DELETE_VOLUME=true`**: All PVCs (including Kafka, VictoriaMetrics, VictoriaLogs) have been deleted. Historical metric and log data is lost. Full re-deploy required: `ansible-playbook telemetry.yml --tags execute`

- **`DELETE_VOLUME` unset/false (default)**: Sink PVCs (Kafka, VictoriaMetrics, VictoriaLogs) are preserved with historical data intact. Source PVCs (iDRAC, LDMS, etc.) have been removed. Re-deploy will reattach existing volumes: `ansible-playbook telemetry.yml --tags execute`

## Test Flow

### Performance Test Flow

```
1. TEL_NFT_001: Run validate playbook, measure duration
   |-- Assert: rc=0 (playbook succeeded)
   +-- Assert: duration < 30s

2. TEL_NFT_002: Run deploy playbook, measure duration
   |-- Assert: rc=0 (playbook succeeded)
   +-- Assert: duration < 600s

3. TEL_NFT_003: Run cleanup playbook, measure duration
   |-- Assert: rc=0 (playbook succeeded)
   +-- Assert: duration < 300s
```

### Idempotency Test Flow

```
1. TEL_NFT_004: Deploy idempotency
   |-- Run 1: Deploy playbook (initial deployment)
   |-- Run 2: Deploy playbook (idempotent re-run)
   +-- Assert: Both runs exit 0

2. TEL_NFT_005: Cleanup idempotency
   |-- Run 1: Cleanup playbook (initial cleanup; -e Delete_volume=true if DELETE_VOLUME=true)
   |-- Run 2: Cleanup playbook (idempotent re-run; same Delete_volume value)
   +-- Assert: Both runs exit 0

3. TEL_NFT_015: Verify no pods remain
   +-- Assert: kubectl get pods -n telemetry returns 0 pods

4a. TEL_NFT_016 (DELETE_VOLUME=true): Verify no PVCs remain
    +-- Assert: kubectl get pvc -n telemetry returns 0 PVCs

4b. TEL_NFT_017 (DELETE_VOLUME unset/false, default): Verify PVCs preserved
    +-- Assert: kubectl get pvc -n telemetry returns > 0 PVCs
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
TEL_NFT_001: PASS  (validate: 12.3s < 30s)
TEL_NFT_002: PASS  (deploy: 487.2s < 600s)
TEL_NFT_003: PASS  (cleanup: 125.4s < 300s)
TEL_NFT_004: PASS  (deploy idempotent: run1=0, run2=0)
TEL_NFT_005: PASS  (cleanup idempotent: run1=0, run2=0)
TEL_NFT_015: PASS  (0 pods remaining)
TEL_NFT_017: PASS  (PVCs preserved, DELETE_VOLUME unset/false)
TEL_NFT_006: PASS  (kafka-broker: 3/3 recovered in 45s)
TEL_NFT_007: PASS  (idrac-telemetry: 1/1 recovered in 30s)
TEL_NFT_008: PASS  (vmstorage: 3/3, vlstorage: 3/3 recovered)
TEL_NFT_009: PASS  (18/18 PVCs Bound)
TEL_NFT_010: PASS  (4/4 services have endpoints)
TEL_NFT_011: PASS  (query 'up' returned 12 results)
TEL_NFT_012: PASS  (42 pods Running after node reboot in 180s)
TEL_NFT_013: PASS  (cleanup=125s, deploy=487s, 42 pods Running)
TEL_NFT_014: PASS  (VM operator: operational, Strimzi operator: True)
```

With `DELETE_VOLUME=true`, `TEL_NFT_016` runs (and asserts 0 PVCs)
instead of `TEL_NFT_017`:

```
TEL_NFT_016: PASS  (0 PVCs remaining, DELETE_VOLUME=true)
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
