# catalog-editing

## Purpose

Applies single-catalog edits (add/remove packages, pin versions, correct metadata) with correct section placement and impact gating. Use when modifying existing Omnia catalogs with validation and compatibility checks.

## When to Use

Use this skill when you need to:
- Add or remove packages from existing catalogs
- Pin package versions to specific releases
- Correct catalog metadata or group assignments
- Apply changes with automatic impact analysis
- Ensure edits maintain schema validity

## Prerequisites

- Access to target catalog JSON file
- Pre-edit impact gate validation (automatic)
- Schema validation tools
- Write access to catalog repository

## Usage

### Add Package
```
Add curl to the base-os catalog
```

### Remove Package
```
Remove nvidia-driver from gpu-compute catalog
```

### Pin Version
```
Pin RHEL to 10.2 in the slurm catalog
```

## Capabilities

| Capability | Description |
|------------|-------------|
| Pre-Edit Gate | Runs impact analysis before applying changes |
| Section Placement | Ensures changes land in correct group/package sections |
| Metadata Consistency | Maintains consistent package metadata |
| Schema Validation | Validates catalog against schema after edits |
| Path Boundary Enforcement | Restricts writes to catalog repository only |
| Rollback Support | Preserves original catalog for rollback |

## Write-Path Security

Only writes to catalog files under:
- `src/main/samples/catalogs/<os_version>/*.json`

Refuses writes outside catalog repository root, even with explicit paths.

## References

- `references/pre_edit_gate.md` — Pre-edit impact and compatibility gate
- `references/bulk_edit_catalog.md` — Bulk editing procedures
- `src/repo_manager/schemas/catalog_schema.json` — Catalog schema
- `src/build_stream/ai_skills/analysis/impact_analysis.md` — Impact analysis skill

## Workflow

1. **Parse Request**: Extract target catalog, operation, and package/group details
2. **Pre-Edit Gate**: Run impact analysis via `pre_edit_gate.md`
3. **Apply Edit**: Modify catalog JSON with correct section placement
4. **Validate**: Run schema validation on modified catalog
5. **Report**: Summarize changes and validation results

## Limitations

- Single-catalog edits only (not cross-catalog changes)
- Requires pre-edit gate approval
- Path restricted to catalog repository
- Does not create new catalogs (use `catalog-generation`)
