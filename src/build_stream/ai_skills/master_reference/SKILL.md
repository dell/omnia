---
name: catalog-selection-gate
description: Shared support_status decision gate every catalog-authoring skill (Catalog Generation, Catalog Editing's Pre-Edit Gate, Analysis skills) applies before emitting a functional group or package set for an operator-requested selection.
---

## Purpose

This is not a standalone operator-facing skill. It is the shared decision
procedure that Catalog Generation, Catalog Editing, and the Analysis skills
each follow before emitting a functional group or package set for a
selection the operator requested (FR-2, AC-005, NFR-6, ER-BSM-001-nersc-ai-
skills-catalog-authoring). It is channel-agnostic: apply it identically
whether you are running as a coding agent with file-system access or as a
browser-based AI assistant that was only given the file's contents.

## When to apply this gate

Apply this procedure whenever a skill is about to resolve or emit a
selection on one of the axes in `master_reference_file.md`'s **A.1 Selection
Catalogue** table: `os_version`, `architecture`, `stack`, `node_role`,
`gpu`, `storage`, or `network`.

## Procedure

0. **When presenting a menu of choices on an A.1 axis** (rather than reacting
   to a specific request), list only the `option` rows whose `support_status`
   is `supported`. Do NOT include a `planned` or `unsupported` option in the
   presented list "for completeness" or "for context" — every option you
   show should be one the operator can actually pick without triggering a
   refusal. This applies whether the axis has one supported option (e.g.
   `gpu`, where only NVIDIA is `supported`) or several. A `planned`/
   `unsupported` option only enters the conversation if the operator
   explicitly names it themselves, which is Step 5 below, not this step.
1. **Read the A.1 Selection Catalogue table** from `master_reference_file.md`
   in this directory. Read the whole table, not just the row you expect to
   match — you need every row on the requested axis to state alternatives.
2. **Find the row** whose `axis` and `option` match the operator's request
   (case-insensitive, e.g. "amd" and "AMD / ROCm" are the same option).
3. **No matching row found:**
   - Do NOT fabricate a decision or a value.
   - Tell the operator the selection is not recorded in the master
     reference file and is not available offline.
   - Flag the request for manual review or online resolution.
4. **Matching row found, `support_status: supported`:**
   - Allow the selection. Proceed to emit the functional group or package
     set using this table row (and the A.2–A.8 tables it depends on).
5. **Matching row found, `support_status: planned` or `support_status:
   unsupported`:**
   - Refuse the selection. Do NOT emit a functional group or package set
     for it.
   - State the recorded `support_status` value.
   - List every other `option` on the same `axis` whose `support_status`
     is `supported`, drawn from the same A.1 table — these are "the
     alternatives."
   - Do NOT silently substitute one of those alternatives for the
     operator. Only apply an alternative after the operator explicitly
     confirms it.
6. **Disclose offline mode** whenever you resolve step 4 or step 5 without
   online package-repository access: state plainly that the decision was
   made from the master reference file, not a live source (NFR-5).

## Worked examples

**Presenting a menu (Step 0 — supported options only):**
> Catalog Generation reaches Step 1's GPU selection and needs to ask the
> operator what GPU to use. A.1 has two `gpu` rows: NVIDIA (`supported`)
> and AMD / ROCm (`planned`). Present: "GPU options: NVIDIA, or none." Do
> not also list "AMD / ROCm (planned, not yet available)" in that same
> menu — it only comes up if the operator asks for it by name, which
> Step 5 then handles.

**Supported selection (allow):**
> Operator asks for storage "VAST (NFS/RDMA)" on the "slurm" stack.
> A.1 row: `storage | VAST (NFS/RDMA) | supported`.
> Decision: allow. Proceed to A.4 to confirm VAST is valid for "slurm"
> (it is) before emitting the `vast_stack_driver_groupv1` group.

**Planned selection (refuse with alternatives):**
> Operator asks for gpu "AMD / ROCm".
> A.1 row: `gpu | AMD / ROCm | planned` (version pin exists in repository
> configuration; no functional group ships today).
> Decision: refuse. Response: "AMD / ROCm is recorded as `planned`, not
> `supported`, in the master reference file — no functional group ships
> for it today. The supported option on the `gpu` axis is: NVIDIA. I will
> not substitute NVIDIA for you; let me know if you'd like me to use it
> instead."

**Selection absent from the table (flag, do not fabricate):**
> Operator asks for storage "Ceph".
> No A.1 row has `axis: storage, option: Ceph`.
> Decision: refuse. Response: "Ceph is not recorded in the master
> reference file's Selection Catalogue and I don't have online access
> right now, so I can't confirm whether it's supported. Flagging this for
> manual review or a follow-up check once online access is available."

## Regenerating `master_reference_file.md`

See the capture note at the top of `master_reference_file.md` for the
re-derivation process (master catalogs -> repository configuration ->
online sources only for a genuinely unresolvable row). This Story does not
automate that process; a future re-derivation repeats the same read-and-
tabulate steps by hand or, if the team later decides to automate it, that
is separate implementation scope requiring its own Story.
