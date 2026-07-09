# Troubleshooting Guide: LDMS vmstat Metrics Missing from Kafka

## Issue Summary

LDMS vmstat metrics are not appearing in the Kafka `ldms` topic, while other metrics (loadavg, meminfo, procstat2, procnetdev2) work correctly.

---

## Quick Diagnosis

### Step 1: Check if vmstat data is in Kafka

```bash
# SSH to K8s control plane node
ssh <kcp_ip>

# Get Kafka bridge IP
BRIDGE_IP=$(kubectl get svc bridge-bridge-lb -n telemetry -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Create consumer and check for vmstat
curl -s -X POST http://$BRIDGE_IP:8080/consumers/debug-grp \
  -H 'content-type: application/vnd.kafka.v2+json' \
  -d '{"name": "c1", "format": "json", "auto.offset.reset": "latest"}'

curl -s -X POST http://$BRIDGE_IP:8080/consumers/debug-grp/instances/c1/subscription \
  -H 'content-type: application/vnd.kafka.v2+json' \
  -d '{"topics": ["ldms"]}'

# Wait 40 seconds for new data, then poll
sleep 40
curl -s http://$BRIDGE_IP:8080/consumers/debug-grp/instances/c1/records \
  -H 'accept: application/vnd.kafka.json.v2+json' | \
  python3 -c 'import json,sys; r=json.load(sys.stdin); print([x["value"]["instance"] for x in r if "vmstat" in x.get("value",{}).get("instance","")])'

# Cleanup
curl -s -X DELETE http://$BRIDGE_IP:8080/consumers/debug-grp/instances/c1
```

**Expected:** List of vmstat instances like `['scnode.omnia.test/vmstat', ...]`  
**If empty:** vmstat is NOT flowing to Kafka → Continue to Step 2

### Step 2: Check if vmstat sets are READY in LDMS

```bash
# SSH to K8s control plane node
ssh <kcp_ip>

# Check store pod for vmstat set status
kubectl exec -i nersc-ldms-store-slurm-cluster-0 -n telemetry -- bash -c \
  'MUNGE_SOCKET=/run/nersc-munge-key/munge.socket \
   /opt/ovis-ldms/bin/ldmsd_controller \
   --host localhost --port 6001 --auth munge \
   --auth-arg socket=/run/nersc-munge-key/munge.socket -x sock' <<EOF
prdcr_set_status regex=.*vmstat.*
EOF
```

**Expected:** All vmstat sets show `State=READY`  
**If READY but not in Kafka:** The issue is decomposition → Continue to Step 3

### Step 3: Get the actual vmstat schema digest

```bash
# SSH to K8s control plane node
ssh <kcp_ip>

# Get schema digest from any node's vmstat set
kubectl exec -i nersc-ldms-store-slurm-cluster-0 -n telemetry -- bash -c \
  'MUNGE_SOCKET=/run/nersc-munge-key/munge.socket \
   /opt/ovis-ldms/sbin/ldms_ls -x sock \
   -h nersc-ldms-aggr.telemetry.svc.cluster.local -p 6001 \
   -a munge -A socket=/run/nersc-munge-key/munge.socket \
   -v -v <hostname>.omnia.test/vmstat' 2>&1 | head -10
```

**Look for:** `Schema Digest` line — a 64-character hex hash like:
```
C7137D7DBC06557F5256336634062DDD868DCDFFFAD5817C0C7E74969C604D13
```

### Step 4: Check if digest exists in decomp.json

```bash
# SSH to K8s control plane node
ssh <kcp_ip>

# Check current vmstat digests in the store pod
kubectl exec nersc-ldms-store-slurm-cluster-0 -n telemetry -- \
  grep vmstat_decomp /ldms_bin/decomp.json
```

**Compare:** If the digest from Step 3 is NOT listed → This is the root cause

---

## Root Cause

The LDMS `store_avro_kafka` plugin uses `decomp.json` to map schema digests to decomposition definitions. When the kernel adds new vmstat fields (e.g., after OS updates), the schema digest changes. If the new digest is not in `decomp.json`, vmstat data is **silently dropped**.

### Why digests change

The vmstat schema digest is a SHA256 hash of all metric field names and types. When the Linux kernel adds new `/proc/vmstat` fields, the LDMS vmstat sampler includes them, changing the digest.

**Common new fields (RHEL 10.0+):**
- `pgpromote_candidate_nrl`
- `direct_map_level2_collapses`
- `direct_map_level3_collapses`

---

## Resolution

### Option A: Add Missing Digest (Quick Fix)

Add the new digest hash to `decomp.json` in the `digest` section.

#### Step 1: Get the digest hash (from Step 3 above)

```bash
DIGEST="C7137D7DBC06557F5256336634062DDD868DCDFFFAD5817C0C7E74969C604D13"
```

#### Step 2: Update decomp.json in omnia_core container

```bash
# SSH to OIM server, then:
podman exec omnia_core bash -c "
  FILE='/omnia/provision/roles/telemetry/files/nersc-ldms-aggr/scripts/decomp.json'
  
  # Find the last vmstat_decomp line number
  LAST_LINE=\$(grep -n 'vmstat_decomp' \$FILE | tail -1 | cut -d: -f1)
  
  # Add new digest after it
  sed -i \"\${LAST_LINE} a\\    \\\"${DIGEST}\\\" : \\\"vmstat_decomp\\\",\" \$FILE
  
  # Verify
  grep vmstat_decomp \$FILE
"
```

#### Step 3: Update K8s ConfigMap

```bash
# SSH to K8s control plane node
ssh <kcp_ip>

# Export current configmap
kubectl get configmap nersc-ldms-bin -n telemetry -o json > /tmp/cm_backup.json

# Copy updated decomp.json from OIM
scp <oim_ip>:/tmp/decomp_updated.json /tmp/

# Patch configmap
python3 -c "
import json
with open('/tmp/cm_backup.json') as f:
    cm = json.load(f)
with open('/tmp/decomp_updated.json') as f:
    cm['data']['decomp.json'] = f.read()
if 'resourceVersion' in cm.get('metadata', {}):
    del cm['metadata']['resourceVersion']
with open('/tmp/cm_patched.json', 'w') as f:
    json.dump(cm, f)
"

kubectl apply -f /tmp/cm_patched.json
```

#### Step 4: Restart LDMS pods

```bash
kubectl delete pod nersc-ldms-store-slurm-cluster-0 nersc-ldms-aggr-0 -n telemetry

# Wait for pods to be Running
kubectl get pods -n telemetry | grep ldms
```

#### Step 5: Verify vmstat in Kafka (repeat Step 1)

Wait ~60 seconds for data to flow, then verify vmstat appears in Kafka.

---

### Option B: Use Schema Matching (Permanent Fix - Recommended)

Instead of maintaining digest hashes, use the `matches` feature to match by schema name. This is **digest-independent** and will work across kernel updates.

#### Modify decomp.json structure

Change from digest-based matching:
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

To schema-based matching:
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
- No need to update digests when kernel changes
- Works with any kernel version
- Self-maintaining

---

### Option C: Use as_is Decomposition (Simplest)

For vmstat, use `as_is` decomposition which passes through ALL fields without defining them explicitly.

```json
{
  "type": "flex",
  "decomposition": {
    "vmstat_as_is": {
      "type": "as_is",
      "indices": [
        { "name": "time_comp", "cols": ["timestamp", "component_id"] }
      ]
    }
  },
  "matches": [
    { "schema": "vmstat", "apply": "vmstat_as_is" }
  ]
}
```

**Benefits:**
- Automatically includes ALL vmstat fields
- No field list maintenance needed
- Schema name includes digest suffix (e.g., `vmstat_c7137d7`) for tracking

---

## Files and Locations

| Item | Location |
|------|----------|
| decomp.json (source) | `omnia_core:/omnia/provision/roles/telemetry/files/nersc-ldms-aggr/scripts/decomp.json` |
| decomp.json (deployed) | K8s ConfigMap `nersc-ldms-bin` in namespace `telemetry` |
| decomp.json (in pod) | `/ldms_bin/decomp.json` inside `nersc-ldms-store-*` pod |

## Pods to Restart After Fix

| Pod | Namespace | Purpose |
|-----|-----------|---------|
| `nersc-ldms-store-slurm-cluster-0` | telemetry | Stores LDMS data to Kafka |
| `nersc-ldms-aggr-0` | telemetry | Aggregates LDMS data from samplers |

---

## Prevention

1. **Use schema matching** instead of digest hashes (Option B above)
2. **Monitor Kafka topics** for missing plugin data after OS updates
3. **Add automation test** to verify all expected LDMS plugins appear in Kafka
