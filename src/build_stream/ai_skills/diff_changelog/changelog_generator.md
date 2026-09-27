---
name: diff-changelog
description: Standalone AI skill that produces a deterministic, reversible machine-readable diff between two catalog versions, plus a separate human-readable changelog (text and rich HTML) summarizing the change. Channel-agnostic (FR-5.1).
---

## Purpose

Answer "what changed between `<current_catalog>` and `<future_catalog>`?" by
running the existing, deterministic catalog diff/patch engine — never by
hand-comparing two large JSON files or asking a model to eyeball the
difference (`ER-BSM-001-nersc-ai-skills-catalog-authoring`, FR-4.1/FR-4.2,
AC-010). This skill operates entirely offline on the two catalog files
supplied; it does not call any online source.

Two artifacts are always produced, and are never merged into each other:
1. **Machine-readable diff** — a reversible pair (`forward_diff`,
   `reverse_diff`) such that `current_catalog + forward_diff = future_catalog`
   and `future_catalog + reverse_diff = current_catalog`.
2. **Human-readable changelog** — plain-English text, plus a rich HTML
   report, summarizing package/group/functional-layer/base-OS/architecture
   changes and any compatibility/dependency warning found in the diff.

## Inputs You Must Read First

1. The two catalog JSON files (current and future) the operator names or
   pastes.
2. `src/repo_manager/schemas/catalog_schema.json` — the schema gate; a diff
   request against a schema-invalid catalog version must be rejected with
   the specific violation, never emitted as a partial diff.
3. `src/build_stream/ai_skills/master_reference/master_reference_file.md`
   — A.8 Constraint and Co-Requisite Table, specifically CON-004 and
   CON-007, which the changelog's compatibility/dependency warnings cite.

## Procedure

### Step 1 — Run the deterministic diff/patch engine (never hand-diff)

A catalog can hold hundreds of packages; do not attempt to manually compare
two full catalogs and enumerate every add/remove/version-change yourself —
that degrades badly with scale and fails silently (a missed item looks
like a clean diff, not an error). If you have shell access, run the
existing tool:

```bash
python3 src/repo_manager/plugins/module_utils/catalog/catalog_manager.py diff \
  --current <path-to-current-catalog.json> \
  --future <path-to-future-catalog.json> \
  --schema src/repo_manager/schemas/catalog_schema.json \
  --output-forward forward_diff.json \
  --output-reverse reverse_diff.json \
  --output-changelog changelog.md \
  --output-html changelog.html
```

- **Exit code 0:** the diff was computed and the reversibility invariant
  verified. `forward_diff.json`/`reverse_diff.json` are the machine-readable
  artifacts; `changelog.md`/`changelog.html` are the human-readable ones.
- **Exit code 1 with `[ERROR]` lines and "Diff rejected: '<current|future>'
  catalog fails schema validation":** report the specific violation(s)
  verbatim to the operator. Do NOT emit a diff against an invalid catalog,
  and do NOT attempt to guess what the diff "would have been."
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

- `CON-004` (blocking): the future catalog's Kubernetes RPM/image/repo
  version pins disagree. Present this prominently — it is a blocking
  constraint, not a stylistic note.
- `CON-007` (warning): a group removed from one functional layer is still
  referenced by another. Tell the operator which other layer(s) are
  affected, since the "removal" in this catalog does not actually remove
  the group from those other layers.
- **No warnings section content beyond `CON-004`/`CON-007` today.** If the
  operator asks about a different kind of compatibility caveat (e.g. an
  NVIDIA driver / RHEL Compatibility-Matrix caveat), tell them this skill
  does not check that yet — it requires the online Red Hat Compatibility
  Matrix, which is `ER-BSM-001-analysis-skills`'s Compatibility Analysis
  skill, not this offline diff skill. Do not fabricate a caveat to answer
  the question.

## Worked Example

> Operator: "What changed between the RHEL 10.0 and RHEL 10.2
> `service_k8s_x86_64` catalogs?"

Running Step 1 against the real shipped sample catalogs
(`src/main/samples/catalogs/10.0/service_k8s_x86_64.json` and
`src/main/samples/catalogs/10.2/service_k8s_x86_64.json`) produces a
198-operation forward diff (and an exactly-inverse 198-operation reverse
diff — the reversibility invariant holds), 0 package additions/removals
(every package key persists across versions; several package *values*
change, e.g. the source `version` list moving from `["10.0"]` to
`["10.2"]`), and 21 `CON-007` warnings — because the two catalogs' functional
layers are named per-OS-version (`..._rhel_10_0_x86_64` vs.
`..._rhel_10_2_x86_64`), so every group in the "current" (10.0) layer looks
"removed" relative to the "future" (10.2) layer set, while the same group
is still referenced by the 10.2 layers. Present this distinction to the
operator plainly: this is a full base-OS-version cutover, not a
same-layer package change, and the `CON-007` warnings reflect that layer
naming pattern rather than an unintended orphaned reference.

## What This Skill Does Not Do

- It does not check any compatibility caveat that requires an online
  source (e.g. the Red Hat Compatibility Matrix) — that remains
  `ER-BSM-001-analysis-skills`'s Compatibility Analysis skill.
- It does not apply either catalog's changes or generate a release note —
  Release Note Generation is deferred (out of scope for this ER); this
  skill only produces the reusable diff/changelog contract a future
  Release Note Generation skill would consume.
- It does not invoke this diff as part of a pre-edit approval flow — that
  orchestration belongs to `ER-BSM-001-catalog-editing-skill`'s Pre-Edit
  Gate (not yet implemented), which calls this skill and then requires
  operator approval before any edit.
