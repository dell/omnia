# bulk-edit-catalog

## Purpose

Applies a requested change consistently across every catalog it affects, with per-catalog schema-validation failure isolation, subject to the Pre-Edit Impact & Compatibility Gate. Use when an edit must be applied identically across more than one catalog, not just a single file.

## When to Use

Use this skill when you need to:
- Apply the same package/version/metadata change across every catalog that matches a condition (e.g. "pin RHEL 10.0 to 10.2 everywhere")
- Get a per-catalog applied/skipped/held/unchanged report for a cross-catalog change
- Isolate one catalog's schema-validation failure from every other catalog's already-completed write

## Prerequisites

- `src/build_stream/ai_skills/catalog-editing/references/pre_edit_gate.md` — the shared Pre-Edit Gate this skill runs per catalog
- `src/build_stream/ai_skills/catalog-editing/SKILL.md` — the underlying single-catalog edit mechanics this skill reuses per catalog
- `src/repo_manager/schemas/catalog_schema.json` — the per-catalog schema gate
- Write access to the catalog repository

## Usage

### Bulk version pin
```
Pin RHEL from 10.0 to 10.2 for service_k8s_x86_64 and slurm_aarch64
```

### Bulk package add
```
Add curl to every catalog with a base_os group
```

## Capabilities

| Capability | Description |
|------------|-------------|
| Per-Catalog Gating | Runs the Pre-Edit Gate independently for every matching catalog |
| Failure Isolation | One catalog's schema failure never affects another's already-completed write |
| Differentiated Approval | Accepts a separate approve/decline decision per flagged catalog |
| Structured Report | Reports applied / skipped (schema-invalid) / held (pending approval) / unchanged (not matching) |
| Write-Path Boundary | Refuses any resolved path outside the catalog repository root, for every catalog in the set |

## Write-Path Security

Only writes to catalog files under:
- `src/main/samples/catalogs/**/*.json` (recursively — flat, versioned, or
  `hybrid/` subtrees are all covered by the same root)

Every resolved path is validated with `resolve_and_validate_catalog_path()` (see `catalog-editing/SKILL.md`'s Write-Path Boundary section) before any write, for every catalog in the bulk set.

## References

- `src/build_stream/ai_skills/catalog-editing/references/pre_edit_gate.md` — shared Pre-Edit Gate
- `src/build_stream/ai_skills/catalog-editing/SKILL.md` — single-catalog edit mechanics
- `src/build_stream/ai_skills/impact-analysis/SKILL.md` — Impact Analysis (invoked per catalog by the gate)
- `src/build_stream/ai_skills/compatibility-analysis/SKILL.md` — Compatibility Analysis (invoked per catalog by the gate)
- `src/repo_manager/schemas/catalog_schema.json` — catalog schema

## Workflow

1. **Identify every matching catalog** — list every match before proceeding
2. **Run the Pre-Edit Gate per catalog** — a finding on one catalog never blocks another
3. **Apply, per catalog, only after that catalog's approval**
4. **Report** applied / skipped / held / unchanged, explicitly

## Limitations

- Single-catalog edits with no cross-catalog scope are the `catalog-editing` skill's responsibility, not this skill's
- Anything the Pre-Edit Gate declines, per catalog, is not applied
