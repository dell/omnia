---
name: skill-working-directory
description: Shared convention for where a catalog-authoring or diff/changelog skill puts intermediate files (pre-edit snapshots, generated diffs, generated changelogs) it needs mid-procedure but that are not the final deliverable, and how it cleans them up. Referenced (not duplicated) by catalog_generation, catalog_editing, and diff_changelog. Channel-agnostic (FR-5.1).
---

## Purpose

Several skills in this ER need a scratch file mid-procedure that is not
itself a requested deliverable:

- `edit_catalog.md`/`bulk_edit_catalog.md` need a **pre-edit snapshot** of a
  catalog so a diff/changelog can still be generated after the edit has
  already overwritten the original file in place (see `pre_edit_gate.md`
  Step 4).
- `changelog_generator.md` needs a place for `forward_diff.json`,
  `reverse_diff.json`, and the rendered changelog files when the operator
  hasn't named specific output paths.
- `catalog_generation/SKILL.md` needs a place for a draft catalog while it is
  still being validated/iterated on, before it is written to its final
  location in Step 6.

This file defines one shared convention for all of them, so a scratch file
from one skill invocation never gets mistaken for a real deliverable, never
collides with another concurrent invocation, and never gets left behind.

## The Convention

**When you have shell access** (coding-agent channel):

1. At the start of the procedure, create one working directory for this
   invocation:
   ```bash
   WORKDIR=$(mktemp -d -t omnia-catalog-skill.XXXXXX)
   ```
   Do not reuse a previous invocation's working directory, and do not create
   scratch files directly inside the catalog repository tree
   (`src/main/samples/catalogs/...`) or any other tracked location — a
   scratch file is never a git-tracked artifact.
2. Put every intermediate file for this invocation under `$WORKDIR`
   (pre-edit snapshots, `forward_diff.json`/`reverse_diff.json`, intermediate
   changelog renders, a draft catalog still being validated). Name files
   descriptively (e.g. `$WORKDIR/pre_edit_snapshot.json`,
   `$WORKDIR/forward_diff.json`) since several may coexist.
3. **Only ever copy a file out of `$WORKDIR`** to its real destination
   (a path the operator named, or the catalog repository path Step 6/Step 3
   of the calling skill resolves) after that destination has itself passed
   whatever validation the calling skill requires. Never treat a path inside
   `$WORKDIR` as a final deliverable.
4. **Clean up at the end of the procedure**, whether it succeeded, was
   declined, or failed partway:
   ```bash
   rm -rf "$WORKDIR"
   ```
   Do this even when the operator declines an edit or a schema validation
   fails — a scratch snapshot from a declined or failed attempt is not
   evidence that needs to persist (that's what the Pre-Edit Gate's audit log
   is for; see `pre_edit_gate.md`'s Auditability section). If the operator
   explicitly asks to keep an intermediate artifact (e.g. "keep the diff
   file too"), copy it to a path they name before cleanup, same as step 3.

**When you do not have shell access** (browser-based assistant): there is no
local filesystem to scratch onto in the first place. Keep every intermediate
artifact (a pre-edit snapshot, a diff) in the conversation as text/JSON you
can refer back to later in the same session, and say so explicitly — do not
claim a working directory was created in a channel that has none.

## What This Is Not

- Not a replacement for the Write-Path Boundary in `edit_catalog.md` and
  `bulk_edit_catalog.md` (NFR-2, Req-SEC-I-1/I-4) — that boundary governs
  where a *final* catalog write lands; this convention governs where
  *scratch* files live before that write happens. A scratch file under
  `$WORKDIR` is never itself a catalog write.
- Not a persistence mechanism. If something must survive past this
  invocation (an audit-log line, a generated changelog the operator asked to
  keep), it is copied to its real destination before `$WORKDIR` is removed,
  per step 3/4 above — it never stays in `$WORKDIR` as the record of record.
