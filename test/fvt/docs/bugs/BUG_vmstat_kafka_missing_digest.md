# Bug Report: LDMS vmstat Metrics Not Flowing to Kafka

## Bug ID
OMNIA-TEL-001

## Title
LDMS vmstat metrics missing from Kafka topic due to unregistered schema digest in decomp.json

## Severity
**High** — vmstat is one of the core LDMS sampler plugins. All vmstat telemetry data was silently dropped, with no error logs.

## Component
`provision/roles/telemetry/files/nersc-ldms-aggr/scripts/decomp.json`

---

## Symptom

- All LDMS sampler plugins (loadavg, meminfo, procstat2, procnetdev2) were producing data to the Kafka `ldms` topic **except vmstat**.
- No errors or warnings in any LDMS pod logs (aggr, store). The vmstat metric sets showed `READY` state in both aggregator and store.
- The store pod logs only contained `oversampled` messages — no decomposition errors were logged.
- Telemetry automation test `test_ldms_data_in_kafka` failed because vmstat instances were missing from Kafka consumer records.

## Root Cause

The `store_avro_kafka` LDMS plugin uses a **decomposition file** (`decomp.json`) to map LDMS metric schemas to Kafka Avro records. Each schema is identified by a **SHA256 digest hash**. The `digest` section of `decomp.json` maps these hashes to decomposition definitions.

The vmstat sampler plugin on the provisioned nodes (LDMSD v4.5.1, RHEL 10.0 kernel) produces a schema with fields that generate the digest hash:

```
C7137D7DBC06557F5256336634062DDD868DCDFFFAD5817C0C7E74969C604D13
```

This hash was **not present** in the `digest` section of `decomp.json`. The store plugin silently skipped vmstat data because it could not find a matching decomposition definition.

### Full Field Count Analysis

| Source | Field Count | Notes |
|--------|-------------|-------|
| `/proc/vmstat` on node | 194 | Kernel 6.12.0-55.82.1.el10_0.x86_64 |
| decomp.json vmstat_decomp | 197 cols | 193 vmstat + 4 meta (timestamp, producer, instance, component_id) |

**LDMS vmstat sampler adds these fields beyond `/proc/vmstat`:**
- `component_id` (meta field)
- `job_id` (Slurm job tracking)
- `app_id` (application tracking)
- `nr_unstable` (legacy field, always 0)

**Fields in decomp.json but NOT in `/proc/vmstat`:**
- `timestamp`, `producer`, `instance`, `component_id` (meta fields)
- `job_id`, `app_id` (LDMS additions)

**Fields in `/proc/vmstat` but NOT in decomp.json (the missing 3):**
| Field | Description |
|---|---|
| `pgpromote_candidate_nrl` | Page promotion candidate (no reclaim list) — newer NUMA balancing counter |
| `direct_map_level2_collapses` | Direct mapping level 2 collapse counter |
| `direct_map_level3_collapses` | Direct mapping level 3 collapse counter |

These 3 kernel fields were added in newer RHEL 10.0 kernels. Their presence changes the LDMS schema structure, producing a different SHA256 digest.

The existing 3 vmstat hashes in decomp.json correspond to older kernel versions with fewer vmstat fields.

### Why This Will Recur

**Every ~3 months** when kernel updates add/remove `/proc/vmstat` fields, the schema digest will change and vmstat data will silently stop flowing to Kafka until a new digest is added.

---

## Diagnosis Steps

### 1. Verified vmstat data was missing from Kafka

Created a Kafka REST proxy consumer and polled the `ldms` topic:

```bash
# On kcp1 (172.16.107.96)
BRIDGE_IP=$(kubectl get svc bridge-bridge-lb -n telemetry -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Create consumer, subscribe to ldms topic, poll records
curl -s -X POST http://$BRIDGE_IP:8080/consumers/debug-grp \
  -H 'content-type: application/vnd.kafka.v2+json' \
  -d '{"name": "c1", "format": "json", "auto.offset.reset": "earliest"}'

curl -s -X POST http://$BRIDGE_IP:8080/consumers/debug-grp/instances/c1/subscription \
  -H 'content-type: application/vnd.kafka.v2+json' \
  -d '{"topics": ["ldms"]}'

# Result: Found loadavg, meminfo, procnetdev2, procstat2 for all nodes
# vmstat was MISSING for all nodes
```

### 2. Confirmed LDMS sets were READY (data was being collected)

```bash
# On kcp1 — check aggregator
kubectl exec -i nersc-ldms-aggr-0 -n telemetry -- bash -c \
  'MUNGE_SOCKET=/run/nersc-munge-key/munge.socket \
   /opt/ovis-ldms/bin/ldmsd_controller \
   --host localhost --port 6001 --auth munge \
   --auth-arg socket=/run/nersc-munge-key/munge.socket -x sock' <<EOF
prdcr_set_status regex=.*vmstat.*
EOF

# Result: All 5 vmstat sets showed State=READY
# scnode.omnia.test/vmstat  READY
# snode1.omnia.test/vmstat  READY
# snode2.omnia.test/vmstat  READY
# lcnode.omnia.test/vmstat  READY
# lnode.omnia.test/vmstat   READY
```

### 3. Retrieved the actual schema digest hash

```bash
# On kcp1 — use ldms_ls -v -v to show schema digest
kubectl exec -i nersc-ldms-store-slurm-cluster-0 -n telemetry -- bash -c \
  'MUNGE_SOCKET=/run/nersc-munge-key/munge.socket \
   /opt/ovis-ldms/sbin/ldms_ls -x sock \
   -h nersc-ldms-aggr.telemetry.svc.cluster.local -p 6001 \
   -a munge -A socket=/run/nersc-munge-key/munge.socket \
   -v -v scnode.omnia.test/vmstat'

# Result:
# Schema Digest: C7137D7DBC06557F5256336634062DDD868DCDFFFAD5817C0C7E74969C604D13
# This hash was NOT in decomp.json
```

All 5 nodes produced the same digest:

```
scnode:  C7137D7DBC06557F5256336634062DDD868DCDFFFAD5817C0C7E74969C604D13
snode1:  C7137D7DBC06557F5256336634062DDD868DCDFFFAD5817C0C7E74969C604D13
snode2:  C7137D7DBC06557F5256336634062DDD868DCDFFFAD5817C0C7E74969C604D13
lcnode:  C7137D7DBC06557F5256336634062DDD868DCDFFFAD5817C0C7E74969C604D13
lnode:   C7137D7DBC06557F5256336634062DDD868DCDFFFAD5817C0C7E74969C604D13
```

### 4. Identified 3 extra fields in the sampler schema

```bash
# Compared sampler vmstat fields vs decomp.json vmstat_decomp fields
# Sampler has 198 fields (from ldms_ls -l), decomp expects 197

# Fields in sampler but NOT in decomp:
#   pgpromote_candidate_nrl
#   direct_map_level2_collapses
#   direct_map_level3_collapses
```

### 5. Confirmed version mismatch

```
Sampler (on nodes):    LDMSD Version 4.5.1
Aggregator (K8s pod):  LDMSD Version 4.5.2
Store (K8s pod):       LDMSD Version 4.5.2
```

---

## Resolution

**Single-line fix:** Added the missing schema digest hash to the `digest` section of `decomp.json`.

### Diff

```diff
--- a/provision/roles/telemetry/files/nersc-ldms-aggr/scripts/decomp.json
+++ b/provision/roles/telemetry/files/nersc-ldms-aggr/scripts/decomp.json
@@ -736,6 +736,7 @@
     "85CE1C60D0570924DAE5B17758912D1A3ADA2091ABD946E06B9A0240F53F4FD8" : "vmstat_decomp",
     "9292CFE0558DBE06EF95BE5B97A9FA13A3F66CF1523D3E175816F3F0D9C66DD4" : "vmstat_decomp",
     "42EB25BA6239F4883E05847676F9BE49B10BD059A714A1C95A932048A19D8D74" : "vmstat_decomp",
+    "C7137D7DBC06557F5256336634062DDD868DCDFFFAD5817C0C7E74969C604D13" : "vmstat_decomp",
     "F76BA26012C2F1F481AB0C1E0672D438ECFE0C4F7B2B4942AA7067A1FCE51A75" : "mt_slurm_decomp"
   }
 }
```

### Manual fix applied to running cluster

```bash
# 1. Updated ConfigMap
kubectl get configmap nersc-ldms-bin -n telemetry -o json > /tmp/cm_backup.json
# Patched decomp.json in configmap data with the new digest line
kubectl apply -f /tmp/cm_patched.json

# 2. Restarted pods to pick up new ConfigMap
kubectl delete pod nersc-ldms-store-slurm-cluster-0 nersc-ldms-aggr-0 -n telemetry

# 3. Verified vmstat data appeared in Kafka within ~40 seconds
# All 5 nodes: ✓ lcnode, lnode, scnode, snode1, snode2
```

---

## Verification

### Before fix
```
Kafka ldms topic instances:
  ✓ lcnode.omnia.test/loadavg
  ✓ lcnode.omnia.test/meminfo
  ✓ lcnode.omnia.test/procnetdev2
  ✓ lcnode.omnia.test/procstat2
  ✗ lcnode.omnia.test/vmstat          ← MISSING
  ... (same pattern for all 5 nodes)
```

### After fix
```
Kafka ldms topic instances:
  ✓ lcnode.omnia.test/loadavg
  ✓ lcnode.omnia.test/meminfo
  ✓ lcnode.omnia.test/procnetdev2
  ✓ lcnode.omnia.test/procstat2
  ✓ lcnode.omnia.test/vmstat          ← FIXED
  ✓ lnode.omnia.test/vmstat           ← FIXED
  ✓ scnode.omnia.test/vmstat          ← FIXED
  ✓ snode1.omnia.test/vmstat          ← FIXED
  ✓ snode2.omnia.test/vmstat          ← FIXED
```

### Telemetry sanity tests
```
18 passed, 1 failed (iDRAC — unrelated), 34 skipped
All LDMS Kafka tests PASSED including vmstat data verification.
```

---

## Permanent Solution (Recommended)

The current digest-based approach requires manual updates every time the kernel changes `/proc/vmstat` fields. LDMS supports a **schema-matching** approach that is digest-independent.

### Use `matches` instead of `digest` in decomp.json

Change from:
```json
{
  "type": "flex",
  "decomposition": { ... },
  "digest": {
    "HASH1": "vmstat_decomp",
    "HASH2": "vmstat_decomp",
    ...
  }
}
```

To:
```json
{
  "type": "flex",
  "decomposition": { ... },
  "matches": [
    { "schema": "vmstat", "apply": "vmstat_decomp" },
    { "schema": "meminfo", "apply": "meminfo_decomp" },
    { "schema": "procstat2", "apply": "procstat2_decomp" },
    { "schema": "procnetdev2", "apply": "procnetdev2_decomp" },
    { "schema": "loadavg", "apply": "loadavg_decomp" }
  ],
  "default": "as_is_decomp"
}
```

**Benefits:**
- Matches by schema NAME, not digest hash
- Works with ANY kernel version
- No maintenance required when kernel updates add/remove vmstat fields
- Self-documenting configuration

### Alternative: Use `as_is` decomposition for vmstat

For maximum flexibility, use `as_is` decomposition which passes through ALL fields:

```json
{
  "vmstat_as_is": {
    "type": "as_is",
    "indices": [
      { "name": "time_comp", "cols": ["timestamp", "component_id"] }
    ]
  }
}
```

**Benefits:**
- Automatically includes ALL vmstat fields (current and future)
- No field list maintenance
- Schema name includes digest suffix for tracking (e.g., `vmstat_c7137d7`)

---

## Recommendations

1. **Immediate:** Commit the digest fix to the Omnia upstream repo.
2. **Long-term (Recommended):** Switch from `digest` to `matches` in decomp.json to eliminate recurring digest maintenance.
3. **Alternative:** Use `as_is` decomposition for vmstat to automatically include all fields.
4. **Monitoring:** The `store_avro_kafka` plugin silently drops data when it cannot match a digest. Consider adding alerting or logging when a schema digest has no matching decomposition entry.

---

## Related Documentation

- [Troubleshooting Guide: LDMS Kafka vmstat Missing](../troubleshooting/LDMS_Kafka_vmstat_missing.md)
- [LDMS Decomposition Documentation](https://ovis-hpc.readthedocs.io/projects/ldms/en/latest/rst_man/src/decomp/ldmsd_decomposition.html)
