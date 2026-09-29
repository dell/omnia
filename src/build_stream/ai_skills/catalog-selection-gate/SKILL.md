---
name: catalog-selection-gate
description: Validates operator-requested OS families/versions, role architectures, stacks, GPU, storage, and network selections against the Selection Catalogue and verified platform/consumer evidence before emitting groups or packages. Use when generating, editing, or analyzing catalogs, including hybrid-OS requests.
---

Before starting, read `../shared/skill_scope.md` and use only this bundle's
companion skills and shared instructions.

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
selection on one of the axes in `references/master_reference_file.md`'s
**A.1 Selection Catalogue** table: `os_version`, `architecture`, `stack`,
`node_role`, `gpu`, `storage`, or `network`. Also gate `os_family` and each
requested `(role, os_family, os_version, architecture)` assignment: the capture's
OS version rows are not a catalog-wide constraint or evidence for another family.

## OS-family/version and hybrid evidence

Distinguish mixed stack, mixed architecture, and multiple OS family/version pairs.
Read concrete definitions recursively under this checkout's
`src/main/samples/catalogs/`; account for legacy `<version>/`, newer
`<family>/<version>/`, and `hybrid/` layouts. An explicitly operator-designated
catalog root/worktree may provide reference data, but record its revision/path
and distinguish it from the active checkout. It does not change the active schema/runtime or
authorize loading skills from another directory.

The reference table is a snapshot. For a tuple absent from it, require matching
base-group OS metadata, role/group/package definitions, source coverage, and
active consumer support before allowing the selection. No matching evidence
means unresolved, not an invented default or a silent substitution. Existing
`planned`/`unsupported` decisions still follow Step 5; a sample alone does not
override them. Read the relevant consumer contracts before proposing a new
family, not just a free-form schema `os` field.

RHEL 10.2/10.0 hybrid examples demonstrate multi-version role mappings, not
multiple-family runtime support. The inspected schema has no
`deb` package type, and the image-build parser returns one `cluster_os_type`
and indexes base packages by version only. Recheck the active checkout before
accepting a multi-family request. If these limits remain, retain the requested
families and explain the missing provider/consumer support; any output is a
blocked draft, not a supported hybrid catalog. Do not relabel DEB packages as
RPMs or change runtime code as part of this gate.

Apply hardware/storage and stack compatibility to every consuming platform
tuple. An axis marked supported does not mean every combination is supported.
Check exactly one matching base-OS group per layer, mandatory `os` coverage for
each tuple, and OS-family/version/architecture source coverage. `noarch` does
not remove OS compatibility requirements. Scope login/compiler and login
defaults to their associated compute pool; explicit login overrides need their
own supported tuple. Do not create a role/platform cross-product.

## Procedure

0. **When presenting a menu of choices on an A.1 axis** (rather than reacting
   to a specific request), list only the `option` rows whose `support_status`
   is `supported`. Do NOT include a `planned` or `unsupported` option in the
   presented list "for completeness" or "for context" — every option you
   show should be one the operator can actually pick without triggering a
   refusal. For OS families and hybrid tuples not represented by A.1, offer
   only choices established by the evidence checks above; filter other axis
   choices by the consuming tuples too. This applies whether the axis has one supported option or
   several, including explicit opt-outs such as None for GPU. A `planned`/
   `unsupported` option only enters the conversation if the operator
   explicitly names it themselves, which is Step 5 below, not this step.
   For the OS configuration prompt, explicitly offer single-version choices
   and "Both RHEL 10.0 and 10.2 — hybrid" when those versions are supported
   (adapt the versions to the reference data). Hybrid is a request to combine
   selections, not a new A.1 row or approval of every role/platform tuple;
   resolve role placement and verify the combination before emitting groups.
   A free-text invitation to specify another family/version is allowed as
   requirements gathering, clearly marked as needing support verification.
1. **Read the A.1 Selection Catalogue table** from
   `references/master_reference_file.md` in this package. Read the whole
   table, not just the row you expect to match — you need every row on
   the requested axis to state alternatives.
2. **Find the row** whose `axis` and `option` match the operator's request
   (case-insensitive, e.g. "amd" and "AMD / ROCm" are the same option).
   For the GPU prompt, map "none"/"CPU-only" to the existing A.1 GPU None row.
   Display it as `None (CPU-only)` in prompts and summaries, regardless of the
   reference row's legacy label. This is a compute/GPU support choice, not a
   catalog type. Explain once that None omits NVIDIA GPU driver/CUDA groups;
   it does not establish whether the machines physically contain GPUs.
   For OS selections, expand "both"/"hybrid" into the requested versions and
   check each role's tuple; clarify ambiguous version sets instead of selecting
   one version or looking for a literal `hybrid` support-status row.
   For the InfiniBand yes/no prompt, map Yes to `InfiniBand (DOCA OFED)`
   and No to `No InfiniBand`. Do not present an Ethernet choice.
   Map normalized stack `mixed` to `slurm + service_k8s`. For PowerScale,
   distinguish NFS export access from Kubernetes CSI; if the access method
   is unspecified, ask rather than silently choosing CSI. The older capture
   has no separate PowerScale NFS row: for plain NFS export access, use the
   supported Generic NFS path and retain PowerScale as the declared provider.
   `src/orchestrator/roles/mount_config/tasks/process_single_mount.yml` processes
   these vendor-neutral mounts; this does not authorize a CSI group.
   An explicit storage
   opt-out emits no conditional storage group and needs no fabricated A.1 row.
3. **No matching row found:**
   - For OS families/versions or hybrid role tuples, use the evidence procedure
     above. If verified, record the evidence and proceed with Step 4's
     compatibility checks; do not fabricate an A.1 row or update the capture.
   - Do NOT fabricate a decision or a value.
   - If still unresolved, tell the operator what is missing from the available
     reference data and flag it for manual review or approved source lookup.
     Online package availability alone does not prove consumer support.
4. **Matching row found, `support_status: supported`:**
   - Allow the selection only after tuple-level compatibility checks. Resolve
     the functional group or package set using the applicable table rows and
     concrete catalog definitions; global RHEL defaults are not other-family
     package definitions.
   - Apply compatibility to role/architecture assignments, not just the
     global architecture set: Kubernetes roles must be x86_64, while mixed
     clusters can have aarch64 Slurm compute. Storage choices are scoped by
     purpose/access method; PowerScale NFS does not imply PowerScale CSI.
     These generation refinements supersede the capture's aggregate "x86_64
     only when Kubernetes is included" note and automatic storage defaults:
     Find `slurm_service_k8s_combined.json` recursively under the approved
     catalog root for the split-role architecture, and inspect hybrid examples
     for per-role OS assignments. Ask about existing cluster storage rather
     than assuming VAST or PowerScale CSI. Keep broader reference-table updates
     separate from this instruction-only change.
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
   online package-repository access: state which master-reference rows, catalog
   files/revisions and consumer contracts support the decision, rather than
   implying live source verification (NFR-5). Do not equate sample availability
   with deployment support or schema validation with deployment verification.

## Worked examples

**Presenting a menu (Step 0 — supported options only):**
> Catalog Generation reaches Step 1's GPU selection and needs to ask the
> operator what GPU to use. A.1 records NVIDIA and None as `supported`
> and AMD / ROCm as `planned`. Present: "GPU support: NVIDIA, or None
> (CPU-only)?" Do
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
> for it today. The supported options on the `gpu` axis are NVIDIA and
> None (CPU-only). I will
> not substitute NVIDIA for you; let me know if you'd like me to use it
> instead."

**Selection absent from the table (flag, do not fabricate):**
> Operator asks for storage "Ceph".
> No A.1 row has `axis: storage, option: Ceph`.
> Decision: refuse. Response: "Ceph is not recorded in the master
> reference file's Selection Catalogue and I don't have online access
> right now, so I can't confirm whether it's supported. Flagging this for
> manual review or a follow-up check once online access is available."

**Hybrid OS versions (verify each role):**
> Operator requests RHEL 10.2/x86_64 Slurm controller and Kubernetes roles,
> RHEL 10.0/aarch64 Slurm compute/compiler, and RHEL 10.0/x86_64 login.
> Inspect `slurm_service_k8s_hybrid_10_2_10_0_combined.json` under the approved
> catalog root: it uses those assignments, three `os` layers, and distinct
> `baseos_group_10.2`/`baseos_group_10.0` dictionary keys. Check the active
> schema/consumers and requested GPU/InfiniBand/storage choices separately;
> the sample is role-mapping evidence, not permission to enable all its groups.

**Multiple OS families (retain intent, block unsupported output):**
> Operator requests RHEL controllers and Ubuntu compute. No verified Ubuntu
> base definitions/provider exist, and consumers still expose one cluster OS
> family. Keep Ubuntu in the unresolved selection record, explain these limits,
> and ask for compatible reference/runtime support. Do not silently generate
> RHEL compute, invent Ubuntu packages, or claim a schema-valid draft is usable.

## Regenerating `master_reference_file.md`

See the capture note at the top of `references/master_reference_file.md` for the
re-derivation process (master catalogs -> repository configuration ->
online sources only for a genuinely unresolvable row). This Story does not
automate that process; a future re-derivation repeats the same read-and-
tabulate steps by hand or, if the team later decides to automate it, that
is separate implementation scope requiring its own Story.
