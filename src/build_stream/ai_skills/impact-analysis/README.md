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
- Master reference file (fallback when online sources unavailable)

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
| Severity Rating | Assigns Critical, High, Medium, Low (or Unresolved) severity per affected layer |
| Online-Preferred | Uses live dnf/repo lookups before falling back to master reference file data |
| Dependency Tracing | Checks surviving dependency paths per affected layer after the full proposed change |
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
| Critical | The cluster cannot provision nodes or schedule jobs |
| High | A whole role or user-facing capability is lost |
| Medium | A degraded or optional feature |
| Low | Cosmetic, or a removal with proven equivalent retention in every affected layer and no other operational effect |
| Unresolved | No severity is supportable from the available evidence (never defaulted to Low) |

## References

- `src/build_stream/ai_skills/compatibility-analysis/SKILL.md` — Compatibility analysis skill
- `references/trusted_source_policy.md` — Trusted source validation policy
- `src/build_stream/ai_skills/shared/connectivity_layer.md` — Online/offline resolution
- `src/build_stream/ai_skills/catalog-selection-gate/references/master_reference_file.md` — Master reference file data

## Workflow

1. **Parse Request**: Extract target (package/group/layer/OS) and catalog
2. **Online Lookup**: Query local dnf, live repos, upstream docs
3. **Dependency Trace**: Expand before/after layers and verify surviving dependency paths for the target OS, architecture, and versions
4. **Tier Analysis**: Assess impact at package/role/cluster/workload levels
5. **Severity Rating**: Assign severity based on scope and criticality
6. **Report**: Generate technical and customer-facing summaries

## Limitations

- Single-catalog analysis only (not cross-catalog)
- Requires connectivity layer for best results
- When online sources are unavailable, uses master reference file (may be incomplete)
- Does not apply changes (analysis only)
- A package definition or dependent in another layer does not prove retention;
  incomplete evidence is reported as unresolved. Retention does not cap the
  risk of a version/source/OS change at Low.
- Uses companion skills only from this bundle (`../shared/skill_scope.md`).
