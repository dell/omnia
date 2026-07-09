# decomp.json Fix Summary

## Problem

LDMS vmstat metrics were not flowing to Kafka because the schema digest hash was not registered in `decomp.json`.

## Root Cause

The `store_avro_kafka` plugin uses digest hashes to match LDMS schemas to decomposition definitions. When the kernel updates add/remove `/proc/vmstat` fields, the schema digest changes, and data is silently dropped.

**Missing digest:** `C7137D7DBC06557F5256336634062DDD868DCDFFFAD5817C0C7E74969C604D13`

**New kernel fields (RHEL 10.0, kernel 6.12.0):**
- `pgpromote_candidate_nrl`
- `direct_map_level2_collapses`
- `direct_map_level3_collapses`

## Fix Applied

### 1. Added new vmstat digest (Quick Fix)

Added the missing digest hash to the `digest` section:

```json
"C7137D7DBC06557F5256336634062DDD868DCDFFFAD5817C0C7E74969C604D13" : "vmstat_decomp",
```

### 2. Added `matches` section (Permanent Fix)

Added schema-based matching that works regardless of digest changes:

```json
"matches" : [
  { "schema" : "dcgm", "apply" : "dcgm_decomp" },
  { "schema" : "loadavg", "apply" : "loadavg_decomp" },
  { "schema" : "lustre_llite", "apply" : "lustre_llite_decomp" },
  { "schema" : "meminfo", "apply" : "meminfo_decomp" },
  { "schema" : "procnetdev2", "apply" : "procnetdev2_decomp" },
  { "schema" : "procstat2", "apply" : "procstat2_decomp" },
  { "schema" : "slingshot_info", "apply" : "slingshot_info_decomp" },
  { "schema" : "slingshot_metrics", "apply" : "slingshot_metrics_decomp" },
  { "schema" : "vmstat", "apply" : "vmstat_decomp" },
  { "schema" : "mt-slurm", "apply" : "mt_slurm_decomp" }
],
```

## Files

| File | Description |
|------|-------------|
| `decomp_with_matches.json` | Updated decomp.json with both `matches` and `digest` sections |
| `decomp.json.backup` | Original file backup (in omnia_core container) |

## Git Diff

```diff
@@ -723,6 +723,18 @@
       ]
     }
   },
+  "matches" : [
+    { "schema" : "dcgm", "apply" : "dcgm_decomp" },
+    { "schema" : "loadavg", "apply" : "loadavg_decomp" },
+    { "schema" : "lustre_llite", "apply" : "lustre_llite_decomp" },
+    { "schema" : "meminfo", "apply" : "meminfo_decomp" },
+    { "schema" : "procnetdev2", "apply" : "procnetdev2_decomp" },
+    { "schema" : "procstat2", "apply" : "procstat2_decomp" },
+    { "schema" : "slingshot_info", "apply" : "slingshot_info_decomp" },
+    { "schema" : "slingshot_metrics", "apply" : "slingshot_metrics_decomp" },
+    { "schema" : "vmstat", "apply" : "vmstat_decomp" },
+    { "schema" : "mt-slurm", "apply" : "mt_slurm_decomp" }
+  ],
   "digest" : {
...
+    "C7137D7DBC06557F5256336634062DDD868DCDFFFAD5817C0C7E74969C604D13" : "vmstat_decomp",
```

## How `matches` Works

According to [LDMS documentation](https://ovis-hpc.readthedocs.io/projects/ldms/en/latest/rst_man/src/decomp/ldmsd_decomposition.html):

> The flex decomposition applies various decompositions by LDMS schema digests **or matches** specified in the configuration.

The `matches` section uses **regex matching** on the schema name, not the digest hash. This means:

- `{ "schema": "vmstat", "apply": "vmstat_decomp" }` matches ANY vmstat schema
- Works with any kernel version
- No maintenance required when kernel updates change vmstat fields

## Deployment Steps

Since K8s cluster is down, when it comes back up:

```bash
# 1. Copy fixed decomp.json to K8s control plane
scp /tmp/decomp_with_matches.json <kcp_ip>:/tmp/

# 2. Update ConfigMap
kubectl get configmap nersc-ldms-bin -n telemetry -o json > /tmp/cm_backup.json

python3 -c "
import json
with open('/tmp/cm_backup.json') as f:
    cm = json.load(f)
with open('/tmp/decomp_with_matches.json') as f:
    cm['data']['decomp.json'] = f.read()
del cm['metadata']['resourceVersion']
with open('/tmp/cm_patched.json', 'w') as f:
    json.dump(cm, f)
"

kubectl apply -f /tmp/cm_patched.json

# 3. Restart LDMS pods
kubectl delete pod nersc-ldms-store-slurm-cluster-0 nersc-ldms-aggr-0 -n telemetry

# 4. Verify vmstat in Kafka after ~60 seconds
```

## Verification

After deployment, verify vmstat data appears in Kafka:

```bash
BRIDGE_IP=$(kubectl get svc bridge-bridge-lb -n telemetry -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Create consumer, subscribe, poll
curl -s -X POST http://$BRIDGE_IP:8080/consumers/verify-grp \
  -H 'content-type: application/vnd.kafka.v2+json' \
  -d '{"name": "c1", "format": "json", "auto.offset.reset": "latest"}'

curl -s -X POST http://$BRIDGE_IP:8080/consumers/verify-grp/instances/c1/subscription \
  -H 'content-type: application/vnd.kafka.v2+json' \
  -d '{"topics": ["ldms"]}'

sleep 40

curl -s http://$BRIDGE_IP:8080/consumers/verify-grp/instances/c1/records \
  -H 'accept: application/vnd.kafka.json.v2+json' | \
  python3 -c 'import json,sys; r=json.load(sys.stdin); vmstat=[x["value"]["instance"] for x in r if "vmstat" in x.get("value",{}).get("instance","")]; print(f"vmstat instances: {len(vmstat)}")'

curl -s -X DELETE http://$BRIDGE_IP:8080/consumers/verify-grp/instances/c1
```

Expected output: `vmstat instances: 5` (one per node)
