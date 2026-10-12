# compatibility-analysis

## Purpose

Cross-references a package or catalog definition against online upstream documentation and the Red Hat Compatibility Matrix, with a disclosed fallback to master reference file data only. Use when confirming whether a package/version is compatible with a target OS, architecture, or another catalog package.

## When to Use

Use this skill when you need to:
- Confirm whether a package/version is compatible with a target OS or architecture
- Confirm whether two packages/versions are compatible with each other
- Replace manual Red Hat Compatibility Matrix research with a disclosed, auditable procedure

## Prerequisites

- `src/build_stream/ai_skills/shared/connectivity_layer.md` — online/offline fallback procedure
- `src/build_stream/ai_skills/impact-analysis/references/trusted_source_policy.md` — approved source classes and audit-logging contract
- `src/build_stream/ai_skills/catalog-selection-gate/references/master_reference_file.md` — A.1/A.6/A.8 offline fallback data

## Usage

### Package/OS compatibility
```
Is nvidia-driver 550.x compatible with RHEL 10.2?
```

### Package/package compatibility
```
Is the kubernetes 1.35 image compatible with the kubernetes-v1-35 repository?
```

## Capabilities

| Capability | Description |
|------------|-------------|
| Online-Preferred | Consults the Red Hat Compatibility Matrix / upstream docs before falling back offline |
| Disclosed Fallback | States plainly when a result is master-reference-file-only |
| No Fabrication | Reports "unresolved" rather than guessing a compatibility verdict |
| Audit Logging | Every degraded-mode event is reconstructable after the fact |

## References

- `src/build_stream/ai_skills/shared/connectivity_layer.md` — online/offline fallback procedure
- `src/build_stream/ai_skills/impact-analysis/references/trusted_source_policy.md` — approved source classes and audit-logging contract
- `src/build_stream/ai_skills/catalog-selection-gate/references/master_reference_file.md` — offline fallback data (A.1, A.6, A.8)

## Workflow

1. **Parse the compatibility question** into package(+version) and target
2. **Attempt the approved online sources** (Red Hat Compatibility Matrix, upstream docs)
3. **Fall back to the master reference file** only on an actual lookup failure, with `disclosure=true`
4. **Report unresolved** rather than fabricate, when neither source has an answer

## Limitations

- Does not replace the changelog's compatibility-warning summary (`catalog-diff` skill), which invokes this skill's logic but packages the result differently
- Never performs an open-ended general web search or consults an unofficial/third-party mirror
