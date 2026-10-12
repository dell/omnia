---
name: bulk-edit-catalog
description: Applies a requested change consistently across every catalog it affects, with per-catalog schema-validation failure isolation, subject to the Pre-Edit Impact & Compatibility Gate. Use when an edit must be applied identically across more than one catalog, not just a single file.
---

Before starting, read `../shared/skill_scope.md` and use only this bundle's
companion skills and shared instructions.

## Purpose

Apply the same logical change — "pin RHEL from 10.0 to 10.2 across all
functional groups," "add a package to every catalog with X" — consistently
across every catalog it affects, and report exactly which catalogs
changed (`ER-BSM-001-nersc-ai-skills-catalog-authoring`, FR-1.3, AC-005).
Every catalog in the bulk edit is gated independently by
`pre_edit_gate.md` (FR-6.1) — a bulk edit is not a bypass of the gate,
it's the gate applied per catalog with per-catalog approval.

## Write-Path Boundary (NFR-2, Req-SEC-I-1/I-4)

Applies per catalog, identically to the `catalog-editing` skill: only write
to a catalog file under the known catalog repository root
(`src/main/samples/catalogs/**/*.json`, recursively — never assume a fixed
directory depth; the shipped topology includes `rhel/<os_version>/*.json`
and `hybrid/*.json` trees), and every resolved path is validated with
`resolve_and_validate_catalog_path()` (see
`src/build_stream/ai_skills/catalog-editing/SKILL.md`'s Write-Path
Boundary section) before any write, for every catalog in the bulk set,
not just the first one.

## Inputs You Must Read First

1. `src/build_stream/ai_skills/catalog-editing/references/pre_edit_gate.md`
   and, for this Story, its per-catalog differentiation section — a bulk
   edit can be clean for some catalogs and flagged for others; each gets
   its own approval decision. It also owns the pre-edit snapshot for each
   catalog, per its Step 4.
2. `src/build_stream/ai_skills/catalog-editing/SKILL.md` — the underlying
   single-catalog edit mechanics this skill applies per-catalog.
3. `src/repo_manager/schemas/catalog_schema.json` — the per-catalog schema
   gate.
4. `src/build_stream/ai_skills/shared/working_directory.md` — use one
   working directory for the whole bulk-edit invocation, with one
   pre-edit snapshot file per catalog inside it (e.g.
   `$WORKDIR/<catalog-name>.pre_edit_snapshot.json`), so a per-catalog
   diff/changelog can be generated for every applied catalog without the
   snapshots colliding with each other.

## Procedure

### Step 1 — Identify every matching catalog

Search the catalog set recursively (`src/main/samples/catalogs/**/*.json` —
do not assume every catalog lives exactly one directory level below
`catalogs/`; a versioned (`rhel/<os_version>/`) or `hybrid/` subtree is
still in scope) for the condition the operator named (e.g. every catalog
with a `base_os` group whose `os_version` is `10.0`). List every match
before proceeding — do not apply to a partial set silently.

### Step 2 — Run the Pre-Edit Gate per catalog

For package additions, use `catalog-editing/SKILL.md`'s dependency-discovery
requirement for each catalog and consuming platform before presenting approvals.
Reuse evidence only for matching package/version/source/platform tuples; check
already-satisfied dependencies and group reachability separately in each catalog.
Show the requested-plus-dependency proposal per catalog, not one assumed common
dependency set. An unpinned or same-repository addition is not exempt.

Run Impact Analysis / Compatibility & Dependency Analysis for the
proposed change against **each** matching catalog independently, per
`pre_edit_gate.md`. A finding on one catalog does not block another:
- Catalogs with no finding (or a disclosed not-applicable check): present
  as "clear to proceed."
- Catalogs with a finding: present the specific finding for that catalog
  only, and require a **separate** approval decision for it.

### Step 3 — Apply, per catalog, only after that catalog's approval

For each catalog the operator approved:

- **If the change is a package add/remove**, reuse the `catalog-editing`
  skill's mechanics (`catalog_manager.py add`/`delete`) once per catalog
  file —
  each invocation reads, validates, and writes exactly one file, so one
  catalog's schema failure cannot affect another's already-completed
  write.
- **If the change is a structural field edit with no dedicated CLI verb**
  (e.g. bumping a `base_os` group's `os_version`, which `add`/`delete`
  don't cover), use the same validate-before-write discipline directly
  via the existing catalog I/O and validator functions — never write a
  new ad hoc mutation path that skips validation:

  ```python
  import sys
  sys.path.insert(0, 'src/repo_manager/plugins/module_utils')
  from catalog.catalog_io import read_catalog, write_catalog
  from catalog.validator import validate_catalog

  catalog = read_catalog(path)
  # ... apply the specific field mutation to catalog['catalog'] ...
  issues = validate_catalog(catalog, schema_path)
  errors = [i for i in issues if i['severity'] == 'error']
  if errors:
      # report and skip -- do NOT write
      ...
  else:
      write_catalog(catalog, path)
  ```

  This is the same pattern `catalog_manager.py`'s `add`/`delete` commands
  now follow (fixed 2026-09-27) — validate the in-memory result, write
  only if it passes.

### Step 4 — Report

List, explicitly:
- **Applied:** every catalog that changed, with the specific change and
  confirmation that its per-catalog changelog (per `pre_edit_gate.md`
  Step 4) was generated and copied to its destination.
- **Skipped (schema-invalid):** every catalog that would have failed
  schema validation after the change, with the specific violation. Its
  file is unmodified — confirm this if asked (e.g. by hash comparison).
- **Held (flagged, awaiting/declined approval):** every catalog whose
  Pre-Edit Gate finding the operator has not yet approved, or explicitly
  declined.
- **Unchanged (not matching):** catalogs that didn't match the original
  condition in Step 1 — explicitly confirm these were left alone, not
  silently included.

No catalog is ever left partially edited: each catalog's mutate-validate
-write sequence is independent and atomic (validate before write, per
catalog), so a failure on one never leaves another half-applied, and
never leaves the failing one itself half-applied either.

## Worked Example (real, verified 2026-09-27)

> Operator: "Pin RHEL from 10.0 to 10.2 for `service_k8s_x86_64` and
> `slurm_aarch64`"

Two real catalogs from `src/main/samples/catalogs/rhel/10.0/`, both with a
`baseos_group` (`type: base_os`) pinned to `os_version: "10.0"`. One
(`slurm_aarch64`, in this trace) is deliberately missing its `os` field
to demonstrate the isolation path with a genuine schema failure, not a
contrived error message.

Running Step 3's field-edit pattern against both files independently:

```json
{
  "applied": ["service_k8s_x86_64.json"],
  "skipped": [
    {
      "path": "slurm_aarch64.json",
      "errors": [
        "Schema validation failed: 'os' is a required property",
        "base_os group 'baseos_group' missing 'os' field"
      ]
    }
  ]
}
```

Verified: `service_k8s_x86_64.json`'s `baseos_group.os_version` is now
`"10.2"` on disk. `slurm_aarch64.json`'s file content is byte-for-byte
identical to before the run (MD5 verified) — the failed catalog was
never written, and the successful catalog's write was unaffected by the
other's failure.

## What This Skill Does Not Do

- Single-catalog edits with no cross-catalog scope (the `catalog-editing`
  skill).
- Anything the Pre-Edit Gate declines, per catalog, or that lacks that
  catalog's specific operator approval.
