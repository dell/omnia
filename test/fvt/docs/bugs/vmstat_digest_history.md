# vmstat Schema Digest History

This document tracks the vmstat schema digest changes across different kernel versions.

## Understanding vmstat Schema Digests

The LDMS vmstat sampler collects all fields from `/proc/vmstat` plus some LDMS-specific fields. The schema digest is a SHA256 hash of all field names and types. When the kernel adds or removes vmstat fields, the digest changes.

## Current Kernel (RHEL 10.0)

**Kernel Version:** `6.12.0-55.82.1.el10_0.x86_64`

**Schema Digest:** `C7137D7DBC06557F5256336634062DDD868DCDFFFAD5817C0C7E74969C604D13`

**Field Count:**
- `/proc/vmstat` fields: 194
- LDMS additions: 6 (timestamp, producer, instance, component_id, job_id, app_id)
- Total LDMS schema fields: 200

**New fields in this kernel (not in older kernels):**
| Field | Description | Added In |
|-------|-------------|----------|
| `pgpromote_candidate_nrl` | Page promotion candidate (no reclaim list) | Kernel 6.x NUMA balancing |
| `direct_map_level2_collapses` | Direct map level 2 collapse counter | Kernel 6.x memory management |
| `direct_map_level3_collapses` | Direct map level 3 collapse counter | Kernel 6.x memory management |

## Historical Digests in decomp.json

The following digests are registered in `decomp.json` for vmstat:

### Digest 1: `85CE1C60D0570924DAE5B17758912D1A3ADA2091ABD946E06B9A0240F53F4FD8`
- **Kernel:** RHEL 8.x / Rocky 8.x (estimated)
- **vmstat fields:** ~180
- **Notes:** Original baseline, older kernels

### Digest 2: `9292CFE0558DBE06EF95BE5B97A9FA13A3F66CF1523D3E175816F3F0D9C66DD4`
- **Kernel:** RHEL 9.0-9.2 (estimated)
- **vmstat fields:** ~185
- **Notes:** Added some NUMA and memory compaction fields

### Digest 3: `42EB25BA6239F4883E05847676F9BE49B10BD059A714A1C95A932048A19D8D74`
- **Kernel:** RHEL 9.3-9.4 (estimated)
- **vmstat fields:** ~190
- **Notes:** Added more memory management counters

### Digest 4: `C7137D7DBC06557F5256336634062DDD868DCDFFFAD5817C0C7E74969C604D13` (NEW)
- **Kernel:** RHEL 10.0 / Kernel 6.12+
- **vmstat fields:** 194 (+ 6 LDMS = 200)
- **Notes:** Added `pgpromote_candidate_nrl`, `direct_map_level2_collapses`, `direct_map_level3_collapses`

## vmstat Field Evolution

### Fields added in recent kernels

| Kernel Version | New Fields |
|----------------|------------|
| 5.x → 6.0 | `pgpromote_success`, `pgpromote_candidate` |
| 6.0 → 6.6 | `direct_map_level2_splits`, `direct_map_level3_splits` |
| 6.6 → 6.12 | `pgpromote_candidate_nrl`, `direct_map_level2_collapses`, `direct_map_level3_collapses` |

### Fields removed in recent kernels

| Kernel Version | Removed Fields |
|----------------|----------------|
| 5.x → 6.x | `nr_unstable` (deprecated, always 0) |

## How to Get Current Digest

```bash
# SSH to K8s control plane
ssh <kcp_ip>

# Get digest from LDMS aggregator
kubectl exec -i nersc-ldms-store-slurm-cluster-0 -n telemetry -- bash -c \
  'MUNGE_SOCKET=/run/nersc-munge-key/munge.socket \
   /opt/ovis-ldms/sbin/ldms_ls -x sock \
   -h nersc-ldms-aggr.telemetry.svc.cluster.local -p 6001 \
   -a munge -A socket=/run/nersc-munge-key/munge.socket \
   -v -v <hostname>.omnia.test/vmstat' 2>&1 | grep -oP '^[A-F0-9]{64}'
```

## How to Check /proc/vmstat Fields

```bash
# On any cluster node
cat /proc/vmstat | wc -l      # Count fields
cat /proc/vmstat | head -20   # View first 20 fields
uname -r                       # Check kernel version
```

## Recommendation

Instead of maintaining digest hashes, use **schema matching** in decomp.json:

```json
"matches": [
  { "schema": "vmstat", "apply": "vmstat_decomp" }
]
```

This matches by schema name (regex), not digest, so it works with ANY kernel version.

See: [LDMS Decomposition Documentation](https://ovis-hpc.readthedocs.io/projects/ldms/en/latest/rst_man/src/decomp/ldmsd_decomposition.html)
