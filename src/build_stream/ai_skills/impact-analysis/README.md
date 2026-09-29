# impact-analysis

## Purpose

Traces operational impact of proposed package/group/layer/OS changes within catalogs across package, role, cluster, and workload tiers with severity ratings. Use when analyzing change impact before catalog modifications or upgrades.

## When to Use

Use this skill when you need to:
- Analyze impact of removing or changing packages
- Understand dependency chains before catalog edits
- Assess severity of proposed changes
- Generate customer-facing impact summaries
- Validate compatibility before upgrades

## Prerequisites

- Target catalog JSON file
- Access to connectivity layer for online lookups
- Local dnf/yum repositories (preferred)
- Master reference file (offline fallback)

## Usage

### Analyze Package Removal
```
What breaks if I remove iproute from the slurm catalog?
```

### Analyze Version Change
```
Analyze impact of upgrading NVIDIA driver to version 550.x
```

### Analyze Group Removal
```
What is the impact of removing ldms_group from compute nodes?
```

## Capabilities

| Capability | Description |
|------------|-------------|
| Multi-Tier Analysis | Traces impact across package, role, cluster, and workload tiers |
| Severity Rating | Assigns CRITICAL, HIGH, MEDIUM, LOW severity to changes |
| Online-Preferred | Uses live dnf/repo lookups before falling back to offline data |
| Dependency Tracing | Identifies reverse dependencies and required-by relationships |
| Customer Summaries | Generates plain-English impact reports |
| Single-Catalog Scope | Analyzes within one catalog (not cross-catalog) |

## Analysis Tiers

1. **Package Tier**: Direct package dependencies and reverse dependencies
2. **Role Tier**: Functional layers and groups affected
3. **Cluster Tier**: Node roles and stack components impacted
4. **Workload Tier**: User applications and services affected

## Severity Levels

| Severity | Criteria |
|----------|----------|
| CRITICAL | Breaks core cluster functionality or prevents boot |
| HIGH | Impacts major services or multiple roles |
| MEDIUM | Affects optional features or single role |
| LOW | Minimal impact, cosmetic, or documentation-only |

## References

- `references/compatibility_analysis.md` — Compatibility analysis procedures
- `references/trusted_source_policy.md` — Trusted source validation policy
- `src/build_stream/ai_skills/shared/connectivity_layer.md` — Online/offline resolution
- `src/build_stream/ai_skills/master_reference/master_reference_file.md` — Offline reference data

## Workflow

1. **Parse Request**: Extract target (package/group/layer/OS) and catalog
2. **Online Lookup**: Query local dnf, live repos, upstream docs
3. **Dependency Trace**: Build forward and reverse dependency graph
4. **Tier Analysis**: Assess impact at package/role/cluster/workload levels
5. **Severity Rating**: Assign severity based on scope and criticality
6. **Report**: Generate technical and customer-facing summaries

## Limitations

- Single-catalog analysis only (not cross-catalog)
- Requires connectivity layer for best results
- Offline mode uses master reference file (may be incomplete)
- Does not apply changes (analysis only)
