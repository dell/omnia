---
name: catalog-diff
description: Produces deterministic, reversible machine-readable diffs between catalog versions plus human-readable changelogs. Use when comparing catalog versions or generating upgrade documentation.
---

Before starting, read `../shared/skill_scope.md` and use only this bundle's
companion skills and shared instructions.

## Purpose

Answer "what changed between `<current_catalog>` and `<future_catalog>`?" by
running the existing, deterministic catalog diff/patch engine — never by
hand-comparing two large JSON files or asking a model to eyeball the
difference (FR-4.1/FR-4.2,
AC-010). This skill operates entirely on the two catalog files without live dependency resolution
supplied; it does not call any online source.

Two artifacts are always produced, and are never merged into each other:
1. **Machine-readable diff** — a reversible pair (`forward_diff`,
   `reverse_diff`) such that `current_catalog + forward_diff = future_catalog`
   and `future_catalog + reverse_diff = current_catalog`.
2. **Human-readable changelog** — plain-English text summarizing
   package/group/functional-layer/base-OS/architecture changes and any
   compatibility/dependency warning found in the diff. A rich HTML report
   is also written when `--output-html` is given **and** the `jinja2`
   library is installed. `jinja2` is not in the build_stream or
   repo_manager requirements; without it the tool prints "HTML report
   requested but jinja2 is not installed -- skipped", still exits 0, and
   writes only the text changelog. Tell the operator when that happens.

## Inputs You Must Read First

1. The two catalog JSON files (current and future) the operator names or
   pastes.
2. `src/repo_manager/schemas/catalog_schema.json` — the schema gate.
   **`--schema` is required** for a semantic diff — without it,
   `catalog_manager.py diff` refuses to run at all unless
   `--allow-schemaless` is explicitly passed, in which case it produces a
   disclosed, degraded text-only comparison (a `SCHEMA-DEGRADED` warning is
   inserted into the changelog itself, not just printed to stdout) rather
   than a silent, potentially misleading semantic conclusion. A diff
   request against a schema-invalid catalog version must be rejected with
   the specific violation, never emitted as a partial diff.
   A missing `jsonschema` dependency or missing/unreadable schema also
   rejects a schema-requested diff. Report the prerequisite failure and
   retry after it is resolved; never silently switch to `--allow-schemaless`.
3. `src/build_stream/ai_skills/catalog-selection-gate/references/master_reference_file.md`
   — A.8 Constraint and Co-Requisite Table, specifically CON-004 and
   CON-007, which the changelog's compatibility/dependency warnings cite.
4. `src/build_stream/ai_skills/shared/working_directory.md` — where to put
   `forward_diff.json`/`reverse_diff.json`/the rendered changelog files when
   the operator (or a calling skill such as `pre_edit_gate.md`) hasn't named
   specific output paths.

## Procedure

### Step 1 — Run the deterministic diff/patch engine (never hand-diff)

A catalog can hold hundreds of packages; do not attempt to manually compare
two full catalogs and enumerate every add/remove/version-change yourself —
that degrades badly with scale and fails silently (a missed item looks
like a clean diff, not an error). If you have shell access, run the
existing tool. When the operator hasn't named specific output paths, write
the outputs into this invocation's working directory
(`shared/working_directory.md`) rather than the current directory:

```bash
python3 src/repo_manager/plugins/module_utils/catalog/catalog_manager.py diff \
  --current <path-to-current-catalog.json> \
  --future <path-to-future-catalog.json> \
  --schema src/repo_manager/schemas/catalog_schema.json \
  --output-forward $WORKDIR/forward_diff.json \
  --output-reverse $WORKDIR/reverse_diff.json \
  --output-changelog $WORKDIR/changelog.md \
  --output-html $WORKDIR/changelog.html
```

Copy `changelog.md`/`changelog.html` (and, if the operator wants them,
`forward_diff.json`/`reverse_diff.json`) to their real destination before
`$WORKDIR` is removed at the end of the procedure.

- **Exit code 0:** the diff was computed and the reversibility invariant
  verified. `forward_diff.json`/`reverse_diff.json` are the machine-readable
  artifacts; `changelog.md` (and `changelog.html`, if `jinja2` is
  installed) are the human-readable ones.
- **Exit code 2 with "--schema is required...":** you omitted `--schema`
  and did not pass `--allow-schemaless` (argparse rejects the command, so
  nothing is written). Add `--schema` (the normal case), or pass
  `--allow-schemaless` only if the operator explicitly accepts a
  degraded, text-only comparison — say so plainly if you do. Exit code 2
  also means another required argument is missing, e.g. one of the
  `--output-*` paths.
- **Exit code 1 with `[ERROR]` lines and "Diff rejected: '<current|future>'
  catalog fails schema validation":** report the specific violation(s)
  verbatim to the operator. Do NOT emit a diff against an invalid catalog,
  and do NOT attempt to guess what the diff "would have been."
- **Exit code 1 with "Diff rejected: '<label>' and '<label>' resolve to the
  same path":** two of `--current`/`--future`/the four `--output-*` paths
  resolve to the same file (including via a symlink) — an output can never
  overwrite an input or another output. Fix the colliding path(s) and
  re-run; nothing was written.
- **Exit code 1 with a legacy-Schema-1.0 error:** the named catalog uses
  the PascalCase `Catalog` root key. Tell the operator to run
  `catalog_manager.py transform` on that file first — this skill does not
  transform 1.0 input itself.

If you do not have shell access in this channel (browser-based assistant),
state that plainly: there is no reliable manual-reasoning fallback for an
exhaustive catalog diff at realistic catalog sizes. Ask the operator (or a
channel with shell access) to run the command above and paste back
`changelog.md`'s content (and, if useful, `forward_diff.json`/
`reverse_diff.json`) for you to narrate or extend.

### Step 2 — Read the changelog, don't re-derive it

`changelog.md` already contains, in this fixed order: package
additions/removals/changes, group changes, functional-layer changes, base
OS/architecture/catalog-metadata impact, and compatibility/dependency
warnings (tagged `CON-004` or `CON-007`, citing the master reference
file's A.8 table). Present this content to the operator; you may add
narrative framing (e.g. grouping by theme, explaining *why* a change
matters) but never contradict or silently drop a line from it — the tool's
output is the fact record, per the no-fabrication rule (NFR-3).

### Step 3 — Surface every warning, never soften a blocking one

- `CON-004` (blocking): the future catalog's Kubernetes RPM, container
  **image tag**, and **repository identifier** version pins disagree —
  e.g. an image tag moving from `1.35` to `1.34` while a sibling RPM stays
  on `1.35`, or a `reponame` drifting to `kubernetes-v1-34` while the RPM
  it sources is still named `kubelet-1.35.1`. Present this prominently —
  it is a blocking constraint, not a stylistic note.
- `CON-007` (warning): a group removed from one functional layer is still
  referenced by another. When the only cause is a base-OS-version layer
  rename, the tool instead emits a single `[INFO] CON-007` cutover line
  listing the affected groups; that is not an orphaned reference. Tell the operator which other layer(s) are
  affected, since the "removal" in this catalog does not actually remove
  the group from those other layers.
- `SCHEMA-DEGRADED` (warning, only present when `--allow-schemaless` was
  used): the diff was computed without a catalog schema. Surface this as
  prominently as any other warning — it means the comparison could not
  distinguish set-like arrays from ordered arrays and validated no
  semantic catalog field.
- **No warnings section content beyond `CON-004`/`CON-007`/`SCHEMA-DEGRADED`
  today.** If the operator asks about a different kind of compatibility
  caveat (e.g. an NVIDIA driver / RHEL Compatibility-Matrix caveat), tell
  them this skill does not check that yet — it requires the online Red Hat
  Compatibility Matrix, which is the `compatibility-analysis` skill, not
  this diff skill. Do not fabricate a caveat to answer the
  question.

## Worked Example

> Operator: "What changed between the RHEL 10.0 and RHEL 10.2
> `service_k8s_x86_64` catalogs?"

Running Step 1 against the real shipped sample catalogs
(`src/main/samples/catalogs/rhel/10.0/service_k8s_x86_64.json` and
`src/main/samples/catalogs/rhel/10.2/service_k8s_x86_64.json`, verified
2026-10-16) produces a 203-operation forward diff and an exactly-inverse
203-operation reverse diff (the reversibility invariant holds). The
changelog reports:

- **Packages: 0 added, 1 removed, 189 changed.** `python3_3_12_9` is
  removed; `python3` changes from `python3-3.12.9` to unpinned `python3`;
  the other 188 changes are only the source `version` moving from
  `["10.0"]` to `["10.2"]`, summarized on one line.
- **Groups: 2 changed. Functional layers: 3 added, 3 removed**, because
  layer names carry the OS version (`..._rhel_10_0_x86_64` →
  `..._rhel_10_2_x86_64`).
- **One `[INFO] CON-007` line** that names the 10 groups that look
  "removed" only because their layers were renamed. It is not an
  orphaned-group warning.

Present this to the operator plainly: it is a full base-OS-version
cutover plus one real package change (`python3_3_12_9` → `python3`),
not a set of same-layer package edits. Without `jinja2` the HTML report
is skipped, as described above.

## What This Skill Does Not Do

- It does not check any compatibility caveat that requires an online
  source (e.g. the Red Hat Compatibility Matrix) — that remains
  the Compatibility Analysis skill.
- It does not apply either catalog's changes or generate a release note —
  Release Note Generation is deferred (out of scope for this ER); this
  skill only produces the reusable diff/changelog contract a future
  Release Note Generation skill would consume.
- It does not run a pre-edit approval flow itself — that orchestration
  belongs to the Pre-Edit Gate
  (`src/build_stream/ai_skills/catalog-editing/references/pre_edit_gate.md`),
  which calls this skill after an approved edit to record the change.
