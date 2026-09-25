---
name: catalog-generation
description: Standalone AI skill that turns an operator-described functional group, base OS, and package list (or a cluster-type description) into a schema-valid Omnia catalog. Channel-agnostic — usable from a coding agent or a browser-based AI assistant (FR-5.1).
---

## Purpose

Generate a schema-valid catalog from an operator's description, by running the
Appendix B selection interview in dependency order, expanding the resulting
selections through the master reference file's Appendix A tables, and never
fabricating a package, version, or repository URL that isn't recoverable
from an online source or the master reference file
(`ER-BSM-001-nersc-ai-skills-catalog-authoring`, FR-1.1, FR-2, AC-005,
AC-009).

This skill implements FR-1.0 (consumption side) and FR-1.1/FR-2 of the parent
ER. It is channel-agnostic: apply every step identically whether you are
running as a coding agent with file-system access or as a browser-based AI
assistant that can only exchange text with the operator. When you lack
file-system access, produce the full catalog JSON as text for the operator
to save themselves, and skip the shell-validation step (state that you could
not run it in this channel).

## Inputs You Must Read First

1. `src/build_stream/ai_skills/master_reference/master_reference_file.md` —
   the 8 Appendix A tables (Selection Catalogue, Node-Role, Functional-Layer
   Composition, Stack-Storage Compatibility, Package Source Defaults, Pinned
   Version, Supported Hardware, Constraint/Co-Requisite).
2. `src/build_stream/ai_skills/master_reference/SKILL.md` — the shared
   `support_status` Selection Catalogue gate (allow/refuse/no-silent-
   substitution). Apply it at every decision point below.
3. `src/build_stream/ai_skills/shared/connectivity_layer.md` — the shared
   online/offline fallback procedure. Apply it whenever you resolve package
   metadata, a compatibility fact, or a version that is not already fixed
   by A.5/A.6.
4. `src/repo_manager/schemas/catalog_schema.json` — the catalog JSON Schema
   the generated output must conform to.

## Step 1 — Selection Interview (Appendix B order)

Elicit selections from the operator in exactly this order. Each step's valid
option set is narrowed by the steps before it — do not reorder this, and do
not ask for a later-step selection before an earlier one is resolved.

| # | Decision | Depends on | Default when deferred | Reference table |
|---|----------|-----------|------------------------|------------------|
| 1 | OS version | — | none — operator must choose | A.1, A.5 |
| 2 | Architecture(s) | 1 | x86_64 | A.1, A.5 |
| 3 | Stack | 1 | none — operator must choose | A.1, A.2, A.4 |
| 4 | Node roles | 2, 3 | all mandatory roles for the stack (A.2) | A.2 |
| 5 | GPU | 4 | none | A.1, A.3, A.7 |
| 6 | Storage | 3 | default_for the chosen stack, from A.4 | A.4 |
| 7 | Network | 4 | InfiniBand attached | A.1, A.3 |
| 8 | Source overrides | 1, 2, 5, 6 | defaults from A.5 | A.5 |

For every selection at steps 1, 2, 3, 5, 6, 7:
- Apply the Selection Catalogue gate (`master_reference/SKILL.md`) before
  offering or accepting the option. Offer only rows whose `support_status`
  is `supported` for the axis, filtered by prior selections.
- If the operator defers a decision that has a recorded default (see table
  above), apply that default and state that you did so.
- If the operator gives a partial description up front (e.g. "minimal
  Slurm-only cluster on RHEL 10.0"), resolve as many steps as the
  description allows before asking about the rest, still in this order.

**Step 2 → Step 3 ordering is load-bearing:** resolve architecture before
stack. Kubernetes (`service_k8s`) is `supported` only on `x86_64` (A.1). If
the operator has already selected `aarch64` when they request
`service_k8s`, do not silently switch either value — see "Constraint
Rejection" below.

**Step 3 → Step 6 ordering is load-bearing:** resolve stack before storage.
Storage options are stack-scoped (A.4 Stack-Storage Compatibility Table).
Never offer a storage option that A.4 does not list as valid for the
already-chosen stack.

**Step 4 gates Steps 5 and 7:** GPU and InfiniBand groups attach per
functional layer (per node role), not per catalog. Do not process GPU or
network selection before node roles are resolved.

Once steps 1–7 are resolved, **restate the full selection set to the
operator for confirmation** before proceeding to Step 8 and catalog
assembly. Do not emit a catalog before this confirmation.

## Step 2 — Stack-Storage Filter and Default Pre-Selection (AC-009)

When presenting storage options at Step 6:

1. Read the A.4 Stack-Storage Compatibility Table.
2. Offer only the storage options whose `valid_for_<chosen stack>` column is
   `yes`. For example, when the stack is `slurm`, offer VAST (NFS/RDMA),
   PowerVault (iSCSI), and Generic NFS — never PowerScale (CSI), which A.4
   marks valid only for `service_k8s`.
3. Pre-select the A.4 `default_for` value that matches the chosen stack
   (VAST for a Slurm functional cluster, PowerScale for a Kubernetes
   functional cluster) and disclose that you are proposing this default.
4. Allow the operator to override the default. If the operator explicitly
   asks for an option A.4 excludes for the chosen stack, state the specific
   reason (citing the A.4 row) rather than silently substituting or
   silently complying.
5. Remember that PowerVault and Generic NFS contribute **no catalog
   group** — they are orchestrator-side, runtime-discovered configuration.
   Do not add a group to the catalog for either.

## Step 3 — Architecture/Stack Constraint Rejection

Before accepting the combination of Step 2 (architecture) and Step 3
(stack):

1. Check A.1: `stack=service_k8s` has `support_status: supported` with the
   note "x86_64 only".
2. If the operator has selected (or is selecting) `aarch64` **and**
   `service_k8s` together:
   - Reject the combination. Do not emit a catalog for it.
   - State plainly: "Kubernetes is supported only on x86_64 in this
     release."
   - Offer exactly two corrective options: change architecture to
     `x86_64`, or change the stack to `slurm`. Wait for the operator's
     choice — do not pick one for them.
3. This check re-applies if the operator changes either selection later in
   the interview (e.g. adds `service_k8s` to an already-`aarch64` catalog
   request).

## Step 4 — Functional-Layer Expansion (A.3)

Once steps 1–8 are confirmed:

1. For every selected node role (Step 4) and every selected architecture
   (Step 2), emit one functional layer named per the A.2
   `layer_name_pattern` (`<role>_rhel_<os_version>_<architecture>`, with
   dots in `os_version` replaced by underscores, matching the shipped
   catalogs, e.g. `slurm_node_rhel_10_0_x86_64`).
2. Populate that layer's `components` array by reading the A.3 row for the
   role:
   - Include every group whose `inclusion` is `always`.
   - Include a `conditional` group only when its `governed_by` selection
     was actually chosen (e.g. include `nvidia_stack_driver_groupv1` only
     when GPU=NVIDIA was selected for a `gpu_capable` role; include
     `vast_stack_driver_groupv1` only when storage=VAST was selected).
3. Do not invent a group name that does not appear in A.3 for that role.
   If the operator asks for something A.3 has no row for, treat it as
   Step 6 of the master-reference Selection Catalogue gate: flag it, do
   not fabricate a group.

## Step 5 — Package Source Resolution (A.5, A.6) and Unresolved-Package Handling

For every package referenced by an included group:

1. First check whether the online/offline connectivity layer
   (`shared/connectivity_layer.md`) can resolve version and source
   metadata for it. Prefer that path.
2. If offline, resolve `pinned_version` and `pin_location` from A.6, and
   `source_kind`/`default_url`/`gpgkey` from A.5, keyed by the resolved
   `os_version` and `architecture`.
3. **`operator_supplied_repo` sources (`slurm_custom`, `ldms`, `vast`)
   have no default URL by design.** Emit the package referencing the
   repository by name (`reponame`), and separately report that repository
   as requiring an operator-supplied URL before the catalog can sync. Do
   not invent a URL for it.
4. If a requested package is absent from both the online source and the
   master reference file (A.5/A.6):
   - Do NOT fabricate its version, architecture, or repository/registry.
   - Still emit the rest of the catalog.
   - Flag that specific package in the output for manual review, and
     state that resolution was attempted only against the master
     reference file (when offline) or which online source was consulted
     (when online).
5. Every emitted package entry SHALL include resolved `version`,
   `architecture` (inside its `sources[]` entries), and repository/registry
   source metadata — matching the shape already used by shipped catalogs
   under `src/main/samples/catalogs/**/*.json` (see `packagetype`,
   `sources[].architecture`, `sources[].reponame` or `sources[].registry`).

## Step 6 — Assemble and Validate the Catalog

1. Assemble the full catalog JSON: `catalog.name`, `catalog.version`,
   `catalog.schema_version` (`2`, matching every shipped catalog),
   `catalog.identifier`, `catalog.description`, `catalog.functionallayer`,
   `catalog.groups`, `catalog.packages`.
2. **Validate before presenting as final.** If you have shell access, run
   the existing catalog validation tool — do not write a new validation
   script:

   ```bash
   python3 src/repo_manager/plugins/module_utils/catalog/catalog_manager.py \
     validate --catalog <path-to-generated-catalog.json> \
     --schema src/repo_manager/schemas/catalog_schema.json
   ```

   - Exit code `0` and no `[ERROR]` lines: the catalog is schema-valid.
     Proceed to Step 7.
   - Any `[ERROR]` line: do NOT present the catalog as final. Report the
     specific violation(s) verbatim and either fix the offending section
     and re-run validation, or (if the violation traces to an unresolved
     package from Step 5) leave that entry flagged rather than
     inventing a fix.
3. If you do not have shell access in this channel (browser-based
   assistant), state that schema validation could not be executed in this
   channel and that the operator (or a channel with shell access) should
   run the command above before syncing.
4. Write the catalog to the expected catalog path
   (`src/main/samples/catalogs/<os_version>/<name>.json` pattern, or the
   path the operator specifies) with no manual post-editing required, when
   you have file-system access. When you do not, return the full catalog
   JSON as text.

## Step 7 — Repository-Name Consistency Reminder

Every generated catalog output SHALL end with a note reminding the operator
to verify that every repository name referenced in the catalog's package
sources is mapped in `repo_manager_config.yml` before syncing — this is the
same reminder required by FR-1.1's last Gherkin scenario. Restate the list
of operator-supplied repositories (from Step 5.3) that still need a URL.

## Worked Example (Appendix B.4)

> Operator: "Generate a catalog for a minimal Slurm-only cluster on RHEL
> 10.0."

| Step | Resolution | Basis |
|------|-----------|-------|
| 1 | RHEL 10.0 | stated |
| 2 | x86_64 | default applied, confirmed |
| 3 | slurm | stated ("Slurm-only") |
| 4 | os, slurm_control_node, slurm_node | mandatory roles; login roles omitted as "minimal" |
| 5 | none | not stated, default none |
| 6 | none | not stated; skill notes VAST is available for this stack |
| 7 | InfiniBand | default applied, confirmed |
| 8 | `slurm_custom` and `ldms` URLs outstanding | A.5 — operator-supplied by design |

Output: three functional layers (`os_rhel_10_0_x86_64`,
`slurm_control_node_rhel_10_0_x86_64`, `slurm_node_rhel_10_0_x86_64`), each
expanded per A.3 with the conditional NVIDIA and VAST groups omitted and the
InfiniBand group included, plus an explicit report that the `slurm_custom`
and `ldms` repository URLs must be supplied before the catalog can sync. No
Slurm version is asserted anywhere, because A.6 records none.

## What This Skill Does Not Do

- Editing an already-generated catalog, bulk edits across catalogs, and the
  Pre-Edit Impact & Compatibility Gate are out of scope here — see
  `ER-BSM-001-catalog-editing-skill` (not yet implemented).
- Impact Analysis and Compatibility & Dependency Analysis are out of scope
  here — see `ER-BSM-001-analysis-skills` (not yet implemented). This
  skill's connectivity layer (`shared/connectivity_layer.md`) is the shared
  foundation that Story depends on.
