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
changed (FR-1.3, AC-005).
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
  file — specifying `os_version=<version>` per package line when possible and
  always passing `--default-os-version` matching each target catalog's
  specific `base_os` OS version —
  each invocation reads, validates, and writes exactly one file, so one
  catalog's schema failure cannot affect another's already-completed
  write.
- **If the change is a structural field edit with no dedicated CLI verb**
  (e.g. moving a catalog from one RHEL minor version to another, which
  `add`/`delete` don't cover), use the same validate-before-write
  discipline directly via the existing catalog I/O and validator
  functions — never write a new ad hoc mutation path that skips
  validation, and always pass `allowed_root` so the write gets the same
  path check and atomic replacement as `--catalog-root`:

  ```python
  import sys
  sys.path.insert(0, 'src/repo_manager/plugins/module_utils')
  from catalog.catalog_io import read_catalog, write_catalog
  from catalog.validator import validate_catalog

  CATALOG_ROOT = 'src/main/samples/catalogs'

  catalog = read_catalog(path)
  # ... apply the specific field mutation to catalog['catalog'] ...
  issues = validate_catalog(catalog, schema_path)
  errors = [i for i in issues if i['severity'] == 'error']
  if errors:
      # report and skip -- do NOT write
      ...
  else:
      write_catalog(catalog, path, allowed_root=CATALOG_ROOT)
  ```

  This is the same pattern `catalog_manager.py`'s `add`/`delete` commands
  follow — validate the in-memory result, write only if it passes. A
  path outside `CATALOG_ROOT` raises `CatalogPathError` and nothing is
  written.

#### Changing a catalog's RHEL version

The OS version is stored in four places, and the consumers read
different ones. Change all of them together, or repo_manager and the
image builder will disagree about the catalog's version while schema
validation still passes:

| Field | Read by |
|---|---|
| Functional-layer names (`<role>_rhel_10_0_<arch>`) | repo_manager: takes the OS version from the layer name (`src/repo_manager/vars/default.yml`) |
| Every package `sources[].version` list | repo_manager: each layer needs a source for its own version, otherwise "has no source for architecture … compatible with rhel X" |
| `base_os` group `os_version` (and its description) | image builder |
| Catalog `name`, `identifier`, `description` | operators and diffs |

```python
def switch_os_version(catalog, old, new):
    """Move every layer, base_os group and package source from `old` to `new`."""
    c = catalog['catalog']
    old_s, new_s = old.replace('.', '_'), new.replace('.', '_')
    for layer in c['functionallayer']:
        layer['name'] = layer['name'].replace(f'_{old_s}_', f'_{new_s}_')
    for group in c['groups'].values():
        if group.get('type') == 'base_os' and group.get('os_version') == old:
            group['os_version'] = new
            group['description'] = group.get('description', '').replace(old, new)
    for package in c['packages'].values():
        for source in package['sources']:
            versions = source.get('version')
            if isinstance(versions, list) and old in versions:
                source['version'] = list(dict.fromkeys(
                    new if v == old else v for v in versions))
    for key in ('name', 'description'):
        c[key] = c[key].replace(old, new)
    c['identifier'] = c['identifier'].replace(old.replace('.', '-'), new.replace('.', '-'))
```

Run this inside the validate-before-write pattern above. It is a
mechanical rename only. Packages whose name or pin is specific to one
minor version (e.g. `python3_3_12_9` on 10.0, plain `python3` on 10.2)
are not changed by it. Compare against the shipped catalog for the
target version, if one exists, and present each such package as a gate
finding for that catalog. Do not swap them silently.

Do not use this on a hybrid catalog, where only some layers move. Edit
the named layers and their sources individually instead.

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

## Worked Example (real, verified 2026-10-16)

> Operator: "Pin RHEL from 10.0 to 10.2 for `slurm_x86_64`,
> `slurm_aarch64` and `service_k8s_x86_64`"

Three real catalogs from `src/main/samples/catalogs/rhel/10.0/`. Each was
moved with `switch_os_version(catalog, '10.0', '10.2')` inside the
validate-before-write pattern, and the result was compared with the
shipped `rhel/10.2/` catalog of the same name:

| Catalog | Gate finding | Result |
|---|---|---|
| `slurm_x86_64` | none | identical to shipped 10.2 |
| `slurm_aarch64` | none | identical to shipped 10.2 |
| `service_k8s_x86_64` | `python3_3_12_9` is a 10.0-specific build; 10.2 uses `python3` in `service_kube_control_plane_group` | same content as shipped 10.2 once the operator approved that replacement (via `catalog-editing` delete + add); only the position of `python3` in the group's `components` differs, because `add` appends |

The two Slurm catalogs were applied while `service_k8s_x86_64` was held
for its own approval, as Step 2 requires.

Isolation path: when one catalog in the set fails validation after the
change (in an earlier trace, a copy of `slurm_aarch64.json` with its
`base_os` group's `os` field removed), it is reported under **Skipped**
with the specific errors (`'os' is a required property`, `base_os group
'baseos_group' missing 'os' field`). Its file stays byte-for-byte
unchanged, and the other catalogs' writes are unaffected.

## What This Skill Does Not Do

- Single-catalog edits with no cross-catalog scope (the `catalog-editing`
  skill).
- Anything the Pre-Edit Gate declines, per catalog, or that lacks that
  catalog's specific operator approval.
