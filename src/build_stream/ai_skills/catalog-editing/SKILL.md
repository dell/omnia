---
name: catalog-editing
description: Applies single-catalog edits (add/remove packages, pin versions, correct metadata) with correct section placement and impact gating. Use when modifying existing Omnia catalogs with validation and compatibility checks.
---

Before starting, read `../shared/skill_scope.md` and use only this bundle's
companion skills and shared instructions.

## Purpose

Apply an operator-requested single-catalog change — "add curl to the
base-os catalog," "remove nvidia-driver from gpu-compute," "pin RHEL to
10.2" — with the change landing in the correct group/package section,
consistent metadata, and the rest of the catalog untouched
(`ER-BSM-001-nersc-ai-skills-catalog-authoring`, FR-1.2, AC-005). Every
edit this skill applies is gated by
`src/build_stream/ai_skills/catalog-editing/references/pre_edit_gate.md` —
there is no "apply an edit" path here that skips it (FR-6.1).

## Write-Path Boundary (NFR-2, Req-SEC-I-1/I-4)

**Only ever write to a catalog file under the known catalog repository
root** (`src/main/samples/catalogs/**/*.json` — recursively, at whatever
depth the shipped catalog topology actually uses today, e.g. a flat
`<os_version>/*.json` layout, a versioned `rhel/<os_version>/*.json`
layout, or a `hybrid/*.json` tree — or the exact path the operator
explicitly names within that tree). Never assume a fixed directory
depth; the boundary is the repository root itself, not any one level
beneath it. This is now a
**code-level control, not just an instruction**: always pass
`--catalog-root src/main/samples/catalogs` to every `catalog_manager.py
add`/`delete` invocation (see the Procedure and Worked Example below).
`catalog_io.resolve_and_validate_catalog_path()` resolves the write
target to an absolute, symlink-free path — following symlinks in the
destination's parent directories *and* the leaf itself — and rejects the
write (nothing is written, `add`/`delete` return exit code 1) if that
resolved path falls outside the given root, whether the escape is an
absolute path elsewhere on the filesystem, a relative path containing
`..`, or a symlink that redirects into it. The write itself is then an
atomic temporary-file replacement (`os.replace()`) within the validated
directory, so an interrupted write never leaves a truncated catalog file
on disk. Never omit `--catalog-root` for a write this skill performs —
without it, `catalog_manager.py` still writes wherever it's told (the
flag is opt-in so the same general-purpose CLI stays usable for
production catalog paths outside this git-tracked sample tree).

## Inputs You Must Read First

1. `src/build_stream/ai_skills/catalog-editing/references/pre_edit_gate.md`
   — run this BEFORE applying any edit. It is not optional for a "trivial"
   edit; a non-applicable analysis is still disclosed, not skipped
   silently. It also owns taking the pre-edit snapshot this skill's edit
   overwrites in place — see its Step 4.
2. `src/repo_manager/schemas/catalog_schema.json` — the schema gate.
3. `src/build_stream/ai_skills/catalog-selection-gate/references/master_reference_file.md`
   — for resolving a package's correct group/section, version, and
   metadata tags when the operator's request doesn't fully specify them.
4. `src/build_stream/ai_skills/shared/working_directory.md` — the
   scratch-file convention `pre_edit_gate.md` uses for the pre-edit
   snapshot and any input files this skill builds (e.g. the
   `catalog_manager.py add`/`delete` input file in the Worked Example
   below).

## Procedure

### Step 1 — Resolve the request to a concrete edit

Identify: the target catalog file, the operation (add / remove / change a
package; pin/change a version; correct a metadata field), and the
specific package/group/field affected. If the operator's request is
ambiguous about which catalog or which package key, ask rather than
guess — per the no-fabrication rule, do not silently pick one candidate
among several plausible package keys.

### Step 2 — Run the Pre-Edit Gate

Follow `pre_edit_gate.md` in full before touching the file. Do not
proceed past this step without either an explicit approval or an
explicit, disclosed "not applicable" determination for each check.

### Step 3 — Apply the edit (only after gate approval)

**If you have shell access, reuse the existing tool — do not hand-edit
the JSON or write a new mutation script:**

- **Add/update a package:** build a small input file in the existing
  `catalog_manager.py` input format (see Worked Example) and run:
  ```bash
  python3 src/repo_manager/plugins/module_utils/catalog/catalog_manager.py add \
    --input <input-file> --catalog <path-to-catalog.json> \
    --default-os-version <the catalog's actual OS version, e.g. 10.2> \
    --schema src/repo_manager/schemas/catalog_schema.json \
    --catalog-root src/main/samples/catalogs
  ```
  **Always pass `--default-os-version` matching the target catalog's own
  version** — the tool's own default is `10.0` and will silently pin a
  new package to the wrong OS version if the target catalog is a
  different version and you omit this flag.
- **Delete a package:** build a delete-input file (see
  `parse_delete_file`'s format) and run:
  ```bash
  python3 src/repo_manager/plugins/module_utils/catalog/catalog_manager.py delete \
    --input <delete-file> --catalog <path-to-catalog.json> \
    --schema src/repo_manager/schemas/catalog_schema.json \
    --catalog-root src/main/samples/catalogs
  ```
- **Both commands validate the in-memory result before writing** (fixed
  2026-09-27) — a schema-violating edit is rejected with the specific
  `[ERROR]` line(s) printed and the file left byte-for-byte unchanged; it
  is never written and then reported as broken. Verify this yourself if
  in doubt: hash the file before and after a rejected edit and confirm
  they match.
- Missing `jsonschema` or a missing/unreadable schema is a blocking
  validation error. Restore the prerequisite and retry; do not omit
  `--schema` or disable validation to complete the edit.

**If you do not have shell access** (browser-based assistant): apply the
same logical change directly to the pasted catalog JSON (add the package
entry with version/architecture/metadata consistent with sibling entries
in the same group; append its key to the group's `components` array),
then return the fully edited catalog content (or a diff) as text. State
that you could not run the schema-validation command in this channel and
that the operator (or a channel with shell access) should validate before
persisting it.

### Step 4 — Confirm scope

Report exactly what changed (the package/group/field) and confirm nothing
else did. "Byte-for-byte unchanged outside the edited section" means: no
other package, group, functional layer, or catalog-metadata field's
*content* differs — not that the raw file bytes outside some byte range
are untouched (the tool always rewrites the whole file via
`json.dump(..., indent=2)`, so the surrounding JSON's literal formatting
is not preserved verbatim; its logical content is what must match).

## Worked Example (real, verified 2026-09-27)

> Operator: "Add curl to the base-os catalog"
> (target: `src/main/samples/catalogs/10.2/service_k8s_x86_64.json`)

After the Pre-Edit Gate determines this is a low-risk addition (Impact
Analysis: `curl` isn't currently in the catalog, so no removal blast
radius applies; Compatibility Analysis: not applicable to a same-repo
RPM addition with no version pin conflict — both disclosed per
`pre_edit_gate.md`) and the operator approves:

Input file (`add_curl.txt`):
```
[baseos_group]
curl, rpm, curl, baseos
```

```bash
python3 src/repo_manager/plugins/module_utils/catalog/catalog_manager.py add \
  --input add_curl.txt --catalog service_k8s_x86_64.json \
  --default-os-version 10.2 \
  --schema src/repo_manager/schemas/catalog_schema.json \
  --catalog-root src/main/samples/catalogs
```

Verified result: `curl` is added to `catalog.packages` with
`{"name": "curl", "packagetype": "rpm", "sources": [{"architecture":
"x86_64", "reponame": "baseos", "name": "rhel", "version": ["10.2"]}]}`
and appended to `baseos_group`'s `components`. Every other package,
every other group, and `catalog.functionallayer` compared dict-equal to
the pre-edit catalog (verified via a real before/after diff, not
assumed).

## What This Skill Does Not Do

- Cross-catalog bulk edits (the `bulk-edit-catalog` skill).
- Anything the Pre-Edit Gate declines or that lacks operator approval.
