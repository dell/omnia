---
name: pre-edit-gate
description: Shared gate every catalog edit (single-catalog or bulk) must pass through before being applied — runs Impact Analysis and Compatibility & Dependency Analysis where applicable, presents findings, requires explicit operator approval, and triggers the post-approval changelog update. Channel-agnostic (FR-5.1).
---

## Purpose

This is not a standalone operator-facing skill. It is the shared
orchestration procedure `edit_catalog.md` and `bulk_edit_catalog.md` both
call before applying any change (FR-6.1 of
`ER-BSM-001-nersc-ai-skills-catalog-authoring`). There is no path in
either editing skill that applies an edit without going through this
gate first — a "trivial" or "metadata-only" edit still runs this
procedure; it may determine a check is not applicable, but that
determination is itself a disclosed step, not a silent bypass.

This is deliberately written as instructions, not a Python state
machine: the gate's job is to run two other skills, present their
findings in natural language, and wait for a human decision — that is
conversational orchestration a model follows identically in either
channel, not a deterministic computation like the diff engine that
needs code to prove an invariant. `TC-UT-009`'s three transition
branches (approve / decline / not-applicable) are verified by tracing
this procedure by hand against each branch, the same evidence style
already used for the master reference file's Selection Catalogue gate.

## Inputs You Must Read First

1. `src/build_stream/ai_skills/shared/working_directory.md` — the
   per-invocation scratch-file convention this gate uses to snapshot a
   catalog before it is edited in place, so a diff/changelog can still
   be generated against the pre-edit state afterward (Step 4).

## States and Transitions

The gate has exactly one active state per catalog per requested edit:

```
findings_pending -> (analysis runs) -> findings_presented
findings_presented --operator approves--> edit_applied -> changelog_updated
findings_presented --operator declines--> unchanged (no edit, no changelog write)
```

A "not applicable" check does not add a fourth terminal state — it
changes what `findings_presented` contains (a disclosed skip instead of
a finding), but the same two transitions (approve -> apply +
changelog; decline -> unchanged) still apply afterward.

## Procedure

### Step 1 — Determine which checks apply

For the requested edit against one catalog:
- **Impact Analysis applies** whenever the edit removes or changes a
  package, group, or functional-layer reference (i.e., anything
  `impact_analysis.md` can trace a blast radius for). It does not apply
  to a pure metadata correction (e.g. fixing a typo in a `description`
  field) that changes no package/group/layer reference.
- **Compatibility & Dependency Analysis applies** whenever the edit
  introduces or changes a version/tag, or adds a package whose
  compatibility with the catalog's declared OS/architecture is not
  already certain from the master reference file's A.1/A.6/A.8 tables.
  It does not apply to a same-version, same-repo package addition with
  no version pin to check.

If a check does not apply, say so explicitly in the findings (see Step
3) — do not simply omit mentioning it.

### Step 2 — Run the applicable checks

- Impact Analysis: invoke
  `src/build_stream/ai_skills/analysis/impact_analysis.md`'s procedure
  against the target catalog and the specific package/group/layer/OS
  target.
- Compatibility & Dependency Analysis: invoke
  `src/build_stream/ai_skills/analysis/compatibility_analysis.md`'s
  procedure against the specific package/version/target.

Both skills already carry their own online-preferred/offline-disclosed
behavior and audit logging (`trusted_source_policy.md`) — do not
duplicate or reinterpret that here; surface their result as-is.

### Step 3 — Present findings and wait for approval

Present, per catalog:
1. Which checks ran, and their result (including severity, if Impact
   Analysis assigned one).
2. Which checks were skipped as not applicable, and why (Step 1).
3. The specific proposed edit, unambiguously described.

**Do not apply the edit yet.** Wait for the operator's explicit
approval or decline for this specific catalog and edit. A generic
"looks fine, go ahead" for an unrelated prior message does not count as
approval for a newly-presented finding.

### Step 4 — Transition on the operator's decision

- **Approve:**
  1. **Before applying the edit**, snapshot the catalog's current
     (pre-edit) content into this invocation's working directory per
     `src/build_stream/ai_skills/shared/working_directory.md` (e.g.
     `$WORKDIR/pre_edit_snapshot.json`). The edit is applied in place
     (`edit_catalog.md`/`bulk_edit_catalog.md` overwrite the catalog file
     directly), so this snapshot is the only remaining copy of the
     "before" state once the write happens — without it, Step 4.2 below
     has nothing to diff against.
  2. Apply the edit via `edit_catalog.md`'s (or, for a cross-catalog
     request, `bulk_edit_catalog.md`'s) mechanics.
  3. Invoke `src/build_stream/ai_skills/diff_changelog/changelog_generator.md`
     with `--current $WORKDIR/pre_edit_snapshot.json --future
     <the now-edited catalog file>` to generate/update its changelog.
     Write the diff/changelog outputs into the same working directory,
     then copy the changelog (and, if the operator wants it, the
     machine-readable diff) to wherever the operator's changelog record
     for this catalog lives, before the working directory is cleaned up.
  4. Report both the applied edit and the changelog update.
  5. Clean up the working directory (including the pre-edit snapshot)
     per `working_directory.md` once the changelog has been copied to
     its real destination.
- **Decline:** do not apply the edit. Do not write to the catalog file.
  Do not generate or update a changelog entry. Do not take a pre-edit
  snapshot in the first place (Step 4.1 is only needed on the approve
  path). Report that the catalog is unchanged.
- **Not-applicable checks still require approval and still update the
  changelog on approval** — "not applicable" only affects which checks
  ran, not whether the gate itself is bypassed. The snapshot-diff-cleanup
  sequence above still applies, even for a metadata-only edit.

### Step 5 — Per-catalog differentiation for bulk edits

When `bulk_edit_catalog.md` is driving a request across multiple
catalogs, run Steps 1-4 **independently per catalog**. A finding on one
catalog never blocks, suppresses, or auto-applies to another:
- Present each catalog's findings separately (a table or per-catalog
  section, not a single merged verdict).
- Step 4's pre-edit snapshot is per catalog, named so multiple snapshots
  in the same working directory don't collide (e.g.
  `$WORKDIR/<catalog-name>.pre_edit_snapshot.json`), and each approved
  catalog's changelog is generated against its own snapshot independently
  of any other catalog's outcome.
- Accept a separate approve/decline decision per flagged catalog. A
  catalog with no finding may be approved and applied while another
  with a finding is still pending or declined — these are independent
  decisions, not a single "all clear" gate for the whole bulk request.
- The bulk-edit report (per `bulk_edit_catalog.md` Step 4) must show,
  per catalog: applied / held-pending-approval / declined / skipped
  (schema-invalid) / unchanged (didn't match).

## Auditability

Every approve/decline/skip decision and every flagged catalog in a bulk
edit must be reconstructable after the fact (NFR-3): what was proposed,
what the finding was (or "not applicable" and why), what the operator
decided, and the outcome. Follow the same audit-logging pattern already
established in `trusted_source_policy.md` — when you have file-system
access, append one line per decision to
`src/build_stream/ai_skills/catalog_editing/pre_edit_gate_audit.log`;
when you don't, state the decision and its outcome explicitly in the
operator-visible response (which is then the only record, same as the
analysis skills' degraded-mode disclosure contract).

## Worked Examples

**Approve, single catalog:**
> Operator asks to remove `nvidia-driver` from `gpu-compute`. Impact
> Analysis reports the direct blast radius (which functional layers
> reference it) plus severity; Compatibility Analysis is not applicable
> (a removal, not a version change). Findings presented; operator
> approves. The pre-edit catalog is snapshotted to `$WORKDIR/
> pre_edit_snapshot.json`, the edit is applied via `edit_catalog.md`, then
> `changelog_generator.md` is invoked with that snapshot as `--current`
> and the now-edited file as `--future` to record the removal and its
> disclosed impact. The changelog is copied to its destination and
> `$WORKDIR` is removed.

**Decline:**
> Same findings as above, but the operator declines. The catalog file
> and any existing changelog remain unchanged — confirm this explicitly
> in the response rather than assuming it's understood.

**Not applicable, still gated:**
> Operator asks to fix a typo in a catalog's `description` field. Impact
> Analysis and Compatibility Analysis are both not applicable (no
> package/group/layer/version touched) — disclose both as skipped and
> why. Approval is still required; on approval, the changelog is still
> updated (a metadata-only entry).

**Bulk edit, differentiated:**
> A bulk request to pin RHEL 10.0 -> 10.2 targets two catalogs.
> Catalog A's Impact/Compatibility checks find nothing; Catalog B's base
> OS group is missing a required field and would fail schema validation
> after the edit (a `bulk_edit_catalog.md`-level finding, reported
> alongside any Impact/Compatibility findings). Present Catalog A as
> clear and Catalog B as flagged, with its specific violation. The
> operator may approve Catalog A while Catalog B remains held (or is
> separately declined) — Catalog A's edit and changelog update proceed
> independently of Catalog B's outcome.
