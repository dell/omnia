# catalog-diff

## Purpose

Produces deterministic, reversible machine-readable diffs between catalog versions plus human-readable changelogs. Use when comparing catalog versions or generating upgrade documentation.

## When to Use

Use this skill when you need to:
- Compare two catalog versions
- Generate upgrade changelogs
- Create reversible diff/patch pairs
- Document catalog changes for customers
- Validate catalog evolution

## Prerequisites

- Two catalog JSON files (current and future versions)
- Access to catalog schema for validation
- Master reference file for context

## Usage

### Generate Diff
```
Generate diff between slurm_v1.0.json and slurm_v1.1.json
```

### Create Changelog
```
Create changelog for upgrade from RHEL 10.0 to 10.2 catalog
```

## Capabilities

| Capability | Description |
|------------|-------------|
| Reversible Diffs | Generates forward and reverse diff pairs |
| Deterministic Output | Same inputs always produce identical diffs |
| Machine-Readable | JSON diff format for automation |
| Human-Readable | Plain text and HTML changelog formats |
| Multi-Level Changes | Tracks package, group, layer, and OS changes |
| Compatibility Warnings | Flags breaking changes and dependencies |

## Output Artifacts

### 1. Machine-Readable Diff
```json
{
  "forward_diff": { /* current → future */ },
  "reverse_diff": { /* future → current */ }
}
```

Properties:
- Deterministic: Same inputs = same output
- Reversible: `current + forward = future`, `future + reverse = current`
- Schema-validated: Both catalogs must be schema-valid

### 2. Human-Readable Changelog

**Plain Text Format:**
- Package additions/removals
- Version changes
- Group modifications
- Functional layer updates
- Architecture changes
- Compatibility warnings

**Rich HTML Format:**
- Color-coded changes
- Expandable sections
- Severity indicators
- Cross-references
- Customer-friendly summaries

## Change Categories

| Category | Description |
|----------|-------------|
| Package Changes | Added, removed, version updates |
| Group Changes | Membership modifications, new/removed groups |
| Layer Changes | Functional layer additions/removals |
| Base OS Changes | OS version or architecture changes |
| Metadata Changes | Catalog identity, description updates |

## References

- `src/repo_manager/schemas/catalog_schema.json` — Catalog schema validation
- `src/build_stream/ai_skills/master_reference/master_reference_file.md` — Reference context

## Workflow

1. **Validate Inputs**: Ensure both catalogs are schema-valid
2. **Parse Catalogs**: Extract functional layers, groups, packages
3. **Generate Forward Diff**: Compute changes from current to future
4. **Generate Reverse Diff**: Compute changes from future to current
5. **Verify Reversibility**: Confirm forward + reverse = identity
6. **Create Changelog**: Generate text and HTML summaries
7. **Flag Warnings**: Identify compatibility/dependency issues
8. **Output**: Deliver diff JSON and changelog artifacts

## Diff Algorithm

- **Deterministic**: Uses sorted keys and stable ordering
- **Comprehensive**: Tracks all catalog sections
- **Reversible**: Forward and reverse diffs are inverses
- **Offline**: No online lookups required

## Limitations

- Requires schema-valid catalogs (rejects invalid inputs)
- Single catalog pair only (not multi-way diffs)
- Offline operation (no live dependency resolution)
- Does not apply diffs (use catalog-editing for that)
