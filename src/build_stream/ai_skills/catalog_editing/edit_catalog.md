---
name: edit-catalog
description: Standalone AI skill that applies a single-catalog edit (add/remove a package, pin a version, correct metadata) with correct section placement, subject to the Pre-Edit Impact & Compatibility Gate. Channel-agnostic (FR-5.1).
---

## Purpose

Apply an operator-requested single-catalog change — "add curl to the
base-os catalog," "remove nvidia-driver from gpu-compute," "pin RHEL to
10.2" — with the change landing in the correct group/package section,
consistent metadata, and the rest of the catalog untouched
(`ER-BSM-001-nersc-ai-skills-catalog-authoring`, FR-1.2, AC-005). Every
edit this skill applies is gated by
`src/build_stream/ai_skills/catalog_editing/pre_edit_gate.md` — there is
no "apply an edit" path here that skips it (FR-6.1).

## Write-Path Boundary (NFR-2, Req-SEC-I-1/I-4)

**Only ever write to a catalog file under the known catalog repository
root** (`src/main/samples/catalogs/<os_version>/*.json`, or the exact
path the operator explicitly names within that tree). Refuse — do not
attempt — any write whose resolved path falls outside that root (e.g. an
absolute path elsewhere on the filesystem, or a relative path containing
`..` that escapes it), even if `catalog_manager.py` itself would not
reject it. This is currently an **instruction-level control, not a
code-level one**: `catalog_manager.py`'s underlying `write_catalog()`
function has no built-in path-boundary check today (verified: it will
write wherever it's told). Treat this skill's own refusal as the
enforcement point until a code-level guard exists, and never rely on the
tool to catch a mistaken or malicious path for you.

## Inputs You Must Read First

1. `src/build_stream/ai_skills/catalog_editing/pre_edit_gate.md` — run
   this BEFORE applying any edit. It is not optional for a "trivial"
   edit; a non-applicable analysis is still disclosed, not skipped
   silently. It also owns taking the pre-edit snapshot this skill's edit
   overwrites in place — see its Step 4.
2. `src/repo_manager/schemas/catalog_schema.json` — the schema gate.
3. `src/build_stream/ai_skills/master_reference/master_reference_file.md`
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
    --schema src/repo_manager/schemas/catalog_schema.json
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
    --schema src/repo_manager/schemas/catalog_schema.json
  ```
- **Both commands validate the in-memory result before writing** (fixed
  2026-09-27) — a schema-violating edit is rejected with the specific
  `[ERROR]` line(s) printed and the file left byte-for-byte unchanged; it
  is never written and then reported as broken. Verify this yourself if
  in doubt: hash the file before and after a rejected edit and confirm
  they match.

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
  --schema src/repo_manager/schemas/catalog_schema.json
```

Verified result: `curl` is added to `catalog.packages` with
`{"name": "curl", "packagetype": "rpm", "sources": [{"architecture":
"x86_64", "reponame": "baseos", "name": "rhel", "version": ["10.2"]}]}`
and appended to `baseos_group`'s `components`. Every other package,
every other group, and `catalog.functionallayer` compared dict-equal to
the pre-edit catalog (verified via a real before/after diff, not
assumed).

## What This Skill Does Not Do

- Cross-catalog bulk edits (`bulk_edit_catalog.md`).
- Anything the Pre-Edit Gate declines or that lacks operator approval.
