---
name: catalog-generation
description: Generates schema-valid Omnia catalogs from operator-described functional groups, base OS, and package lists. Use when creating new catalogs for cluster configurations (Slurm, Kubernetes, or mixed-stack deployments).
---

Before starting, read `../shared/skill_scope.md` and use only this bundle's
companion skills and shared instructions.

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

1. `src/build_stream/ai_skills/catalog-selection-gate/references/master_reference_file.md` —
   the 8 Appendix A tables (Selection Catalogue, Node-Role, Functional-Layer
   Composition, Stack-Storage Compatibility, Package Source Defaults, Pinned
   Version, Supported Hardware, Constraint/Co-Requisite).
2. `src/build_stream/ai_skills/catalog-selection-gate/SKILL.md` — the shared
   `support_status` Selection Catalogue gate (allow/refuse/no-silent-
   substitution). Apply it at every decision point below.
3. `src/build_stream/ai_skills/shared/connectivity_layer.md` — the shared
   online/offline fallback procedure. Apply it whenever you resolve package
   metadata, a compatibility fact, or a version that is not already fixed
   by A.5/A.6.
4. `src/repo_manager/schemas/catalog_schema.json` — the catalog JSON Schema
   the generated output must conform to.
5. `src/build_stream/ai_skills/shared/working_directory.md` — where to put
   the draft catalog while it's still being assembled/validated (Steps 4-6),
   before it is written to its final location.

**Topology dependency:** every A.1–A.8 table row assumes the catalog
topology `references/master_reference_file.md` was last captured against
(see that file's "Topology scope of this capture" note). If
`src/main/samples/catalogs/` now has a versioned `rhel/<os_version>/`
subtree, a `hybrid/` subtree, or a different catalog count than that
capture recorded, treat every count/row here as needing re-verification
before you rely on it — the discovery commands below (`grep -rl`, etc.)
are already recursive and keep working regardless, but the hand-tabulated
rows themselves are not automatically current.

**A.3's known limitation:** the Functional-Layer Composition Table records
which *groups* a role includes, not which *packages* each group actually
contains — the master reference file is explicit about this
(`master_reference_file.md`'s header: "Master catalogs remain the
authoritative source for the concrete package set of an already-shipped
configuration"). A group's package membership only exists in the shipped
catalog JSON files (`src/main/samples/catalogs/**/*.json`) themselves. Step
4b below is the resolution procedure for that gap — read it before you
reach Step 4, since it changes what "the group's packages" means in
practice.

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
| 5 | GPU: NVIDIA or None (CPU-only catalog) | 4 | None, only if explicitly deferred | A.1, A.3, A.7 |
| 6 | Storage | 3 | default_for the chosen stack, from A.4 | A.4 |
| 7 | Include InfiniBand support? Yes / No | 4 | Yes, only if explicitly deferred | A.1, A.3 |
| 8 | Source overrides | 1, 2, 5, 6 | defaults from A.5 | A.5 |
| 9 | Additional packages / custom functional roles | 1–8 | none | Step 4a |

**Step 4 (Node roles) is not a prompted decision:** Do not ask the operator
to choose node roles. Instead, automatically select all roles marked
`mandatory: yes` in the A.2 Node-Role table for the chosen stack, and
disclose which roles you selected. For example, for the Slurm stack, state:
"I've selected the mandatory roles for Slurm: os, slurm_control_node, and
slurm_node." Optional roles (those with `mandatory: no`) are only included
if the operator explicitly requests them in Step 9 (custom roles).

For every selection at steps 1, 2, 3, 5, 6, 7:
- Apply the Selection Catalogue gate (`catalog-selection-gate/SKILL.md`) before
  offering or accepting the option. Per that gate's Step 0, the menu you
  present lists **only** `supported` rows for the axis, filtered by prior
  selections — never include a `planned` or `unsupported` row in the
  presented choices, even as a labeled "not yet available" entry. A
  `planned`/`unsupported` option is handled reactively (the gate's Step 5)
  only if the operator names it themselves.
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

**GPU prompt:** when the request has not already answered Step 5, ask:
"GPU support: NVIDIA, or None (CPU-only catalog, without NVIDIA GPU
driver/CUDA groups)?" Explain that None describes the software being
configured, not whether GPUs are physically present in the machines. NVIDIA
adds the NVIDIA group only to eligible `gpu_capable` roles; None omits it.
If no selected role is GPU-capable, explain that constraint rather than
silently attaching GPU software to an ineligible role. If custom packages
would reintroduce GPU software after None was chosen, clarify that conflict
before assembly.

**InfiniBand prompt:** when the request has not already answered Step 7,
ask "Include InfiniBand support? Yes / No." Yes selects A.1's
`InfiniBand (DOCA OFED)` and includes `infiniband_stack_driver_groupv1`
where A.3 permits it. No selects `No InfiniBand` and omits that group.
Do not present a separate Ethernet option; No makes no assertion about
the site's other network interfaces. Apply a default only when the
operator explicitly defers the question, and disclose it.

Once steps 1–7 are resolved, and before restating the selection set for
confirmation, **always ask Step 9 explicitly**: "Would you like to add any
packages beyond the standard functional-layer composition, or define a
custom functional role not covered by the node roles above?" Do not skip
this question because the operator's initial description sounded complete —
a "minimal Slurm cluster" request may still turn out to need one extra
package or role once asked. If the operator declines or doesn't answer,
proceed with none added and say so. See Step 4a for how an answer here is
applied once catalog assembly reaches functional-layer expansion.

Once steps 1–9 are resolved, resolve the catalog name below, then **restate
the full selection set, catalog name, and output filename for confirmation**
before catalog assembly. Reuse selections and names already supplied by the
operator instead of asking for them again.

### Catalog name

If the operator supplied a name, use it as `catalog.name`. Otherwise offer
two or three names based on the confirmed OS, architecture, and stack and
allow a custom name in the same prompt. For example, for a CPU-only Slurm
catalog on RHEL 10.2 x86_64: "Choose a catalog name: `slurm_cpu_rhel_10_2_x86_64`,
`hpc_slurm_rhel_10_2_x86_64`, or enter your own name." Suggestions must match
the actual selections; do not imply GPU or InfiniBand support when omitted.

Accept any non-empty name that satisfies the catalog schema, including a
human-readable name with spaces. Keep that display name separate from a
proposed filesystem-safe filename stem and `catalog.identifier`; show the
mapping in the final selection confirmation. Do not interpret a display name
as a directory or shell command. Honor an explicitly supplied output path.
If a proposed filename already exists, resolve a new filename or an explicit
edit request before generation. If the operator asks you to choose, use the
first matching suggestion and disclose it; silence alone does not select a
name.

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
   If the operator asks for something A.3 has no row for **and it was not
   raised as a Step 9 additional-package/custom-role answer**, treat it as
   Step 5 of the master-reference Selection Catalogue gate: flag it, do
   not fabricate a group. A Step 9 answer is handled by Step 4a below
   instead of being flagged, because the operator explicitly asked for it
   and it is disclosed as operator-defined rather than presented as if A.3
   already recorded it.

## Step 4a — Custom Functional Roles and Additional Packages (Step 9 Answers)

This step only runs when Step 9 of the interview produced an answer other
than "none." It has two independent parts — an operator may ask for either
or both.

### Additional packages on an existing group

When the operator names a specific package to add beyond a role's standard
A.3 composition (e.g. "also include `htop` on the login nodes"):

1. Resolve the package the same way Step 5 (Package Source Resolution)
   does for every other package — connectivity layer first, A.5/A.6
   offline, never fabricated.
2. Add it to an existing group already included on that layer when one is
   a reasonable fit (e.g. a small utility on `admin_debug_group` rather
   than creating a new group for one package). Name the group you chose
   when you report back what you did.
3. If no existing group is a reasonable fit, treat it as a "new custom
   group" and follow the next section instead of forcing it into an
   unrelated group.

### Custom / flexible functional roles and groups

When the operator names a functional role or group A.2/A.3 has no row for
(e.g. a site-specific monitoring role, or a group bundling packages no
existing group covers):

1. **This is operator-defined content, not a master-reference-file lookup.**
   State that plainly — do not present a custom group as if A.3 already
   recorded it, and do not silently fold it into an existing standard group
   that would misrepresent its purpose.
2. **Validate the custom role's functional-layer name against A.2's
   `layer_name_pattern` before emitting it** — every role in every shipped
   catalog (`os`, `login_node`, `login_compiler_node`,
   `slurm_control_node`, `slurm_node`, `service_kube_control_plane`,
   `service_kube_node`; verified across all 24 shipped functional layers)
   follows the same `<role>_rhel_<os_version>_<architecture>` pattern with
   no exception, so a custom role's layer name must too (e.g.
   `<custom_role>_rhel_10_2_x86_64`). Do not invent a different
   layer-naming scheme for a custom role, and do not let a custom role's
   name collide with an existing one in A.2.
3. **`baseos_group` is the one naming exception, and it works the other
   way — the group name, not the layer name, stays fixed.** Every shipped
   catalog's base-OS group is named exactly `baseos_group` (`type:
   base_os`) regardless of architecture, OS version, or stack — there is no
   per-arch or per-stack variant of this specific group name anywhere in
   `src/main/samples/catalogs/**/*.json` (its *functional layer*, `os_rhel_
   <os_version>_<architecture>`, still follows the normal pattern from
   point 2 above; only the group inside it is invariant). If a custom
   role needs base-OS-level packages, add them to the existing
   `baseos_group` rather than inventing a variant name (e.g.
   `baseos_slurm_group`, `base_os_group`) — flag it to the operator and
   confirm first if their request genuinely seems to call for a separate
   base-OS group.
4. **A custom group that isn't base-OS** is named `snake_case`, ends in
   `_group` (or `_stack_driver_groupv1` if it is specifically a
   hardware/driver stack addition, matching
   `nvidia_stack_driver_groupv1`/`vast_stack_driver_groupv1`'s pattern),
   and does not collide with any name already in A.3 or in the catalog
   being assembled.
5. Resolve every package the new group references the same way Step 5
   resolves every other package (connectivity layer, then A.5/A.6, never
   fabricated).
6. Include the new group in the relevant functional layer's `components`
   array, following the same `always`/`conditional` inclusion logic Step 4
   uses for standard groups.
7. Report the custom group/role explicitly as operator-defined when you
   restate the final selection set and when Step 7's catalog-assembly
   output is presented — this is not something a future diff/changelog
   reader should have to guess at.

## Step 4b — Group Package Composition Resolution

This step resolves, for every **standard** (non-custom) group Step 4
included, which packages actually belong to it — the piece A.3 does not
record. Do this before Step 5, which resolves each package's *version and
source*, not which packages exist in the first place. (Step 4a's custom
groups already have their package list stated by the operator and do not
go through this step.)

1. **Search every shipped catalog for this exact group name**, not just the
   catalog nearest the requested stack/arch/os_version. This search is
   already recursive and topology-agnostic — it does not assume catalogs
   live at any fixed directory depth below `catalogs/`, so it still finds
   every match whether the shipped layout is flat (`<os_version>/*.json`),
   versioned (`rhel/<os_version>/*.json`), or includes a `hybrid/*.json`
   subtree:
   ```bash
   grep -rl '"<group_name>"' src/main/samples/catalogs/
   ```
   or read each candidate file directly if you don't have shell access.
   Collect every instance's `components` package-key set.
2. **No shipped catalog contains this group name at all** (e.g. every
   catalog under `src/main/samples/catalogs/` has been removed, moved, or
   this combination was simply never shipped):
   - Do NOT borrow another group's, another stack's, or another
     architecture's package list as a stand-in, and do NOT fabricate a
     plausible-sounding package set for it.
   - State plainly that this group's concrete package composition has no
     offline source: the master reference file only has its structural
     inclusion (A.3), and no shipped catalog is available to read its
     packages from.
   - Ask the operator to supply this group's package list directly, or to
     restore/point at a catalog file that has it, before this group can be
     populated. Leave it explicitly flagged as unresolved in the meantime —
     do not silently narrow the catalog's scope by dropping the group, and
     do not proceed as if a different stack's package list were an
     acceptable substitute.
3. **Exactly one distinct package-key set exists across every instance
   found** (verified, not assumed — e.g. `common_pks`, `admin_debug_group`,
   and `ldms_group` each have exactly one component-set across all 22
   shipped catalogs that reference them): use it. It does not matter which
   specific catalog file it came from, since every instance already agrees.
4. **More than one distinct package-key set exists across instances found**
   (this does happen for real — e.g. `baseos_group` has 3 distinct
   variants across shipped catalogs, differing only by one
   architecture-specific `image_build_<arch>` package key): pick the
   instance from the catalog file whose stack, architecture, and OS version
   most closely match the one being generated, in that priority order
   (an exact stack+arch+os_version match beats an arch-only match). Name
   the specific source catalog file you used, and if it is not an exact
   match on every axis, disclose exactly which axis differs and why you
   judged it a safe approximation (e.g. "sourced from `slurm_x86_64.json`;
   this catalog's architecture differs from the requested `aarch64`, but
   `baseos_group`'s only variation across shipped catalogs is the
   architecture-specific image-build package, which Step 5 will resolve
   correctly for the target architecture regardless of source file").
5. **Record the source catalog file for every group**, whether it was an
   exact match, a safe identical-composition reuse, or a disclosed
   approximation — this is what lets an operator or a later diff/changelog
   trace where each group's packages came from, and is required in Step
   7's final report alongside the repository-name reminder.

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

1. Assemble the full catalog JSON using the confirmed `catalog.name`,
   filename, and identifier: `catalog.version`,
   `catalog.schema_version` (`2`, matching every shipped catalog),
   `catalog.identifier`, `catalog.description`, `catalog.functionallayer`,
   `catalog.groups`, `catalog.packages`. If you have shell access, write this
   draft into this invocation's working directory per
   `shared/working_directory.md` (e.g. `$WORKDIR/draft_catalog.json`) rather
   than directly at its final path — it is not yet validated, so it is not
   yet a deliverable.
2. **Validate before presenting as final.** If you have shell access, run
   the existing catalog validation tool against the draft — do not write a
   new validation script:

   ```bash
   python3 src/repo_manager/plugins/module_utils/catalog/catalog_manager.py \
     validate --catalog $WORKDIR/draft_catalog.json \
     --schema src/repo_manager/schemas/catalog_schema.json
   ```

   - Exit code `0`, no `[ERROR]` lines, and schema validation actually ran:
     the catalog is schema-valid. A missing `jsonschema` library or an
     unreadable/missing schema is a blocking validation failure, not a
     successful offline fallback. Do not omit `--schema` to get past it.
     Proceed to Step 7.
   - Any `[ERROR]` line: do NOT present the catalog as final. Report the
     specific violation(s) verbatim and either fix the offending section
     and re-run validation, or (if the violation traces to an unresolved
     package from Step 5) leave that entry flagged rather than
     inventing a fix.
3. If you do not have shell access in this channel (browser-based
   assistant), state that schema validation could not be executed in this
   channel and that the operator (or a channel with shell access) should
   run the command above before syncing. Label any returned JSON as an
   unvalidated draft, never as a schema-valid final catalog.
4. Once validation passes, copy the draft from `$WORKDIR` to the expected
   catalog path (`src/main/samples/catalogs/<os_version>/<name>.json`
   pattern, or the path the operator specifies) with no manual post-editing
   required, when you have file-system access. When you do not, return the
   full catalog JSON as text. Either way, remove `$WORKDIR` once the final
   copy has succeeded, per `shared/working_directory.md`.

## Step 7 — Repository-Name Consistency Reminder and Group-Source Traceability

Every generated catalog output SHALL end with a note reminding the operator
to verify that every repository name referenced in the catalog's package
sources is mapped in `repo_manager_config.yml` before syncing — this is the
same reminder required by FR-1.1's last Gherkin scenario. Restate the list
of operator-supplied repositories (from Step 5.3) that still need a URL.

Alongside that reminder, restate Step 4b's per-group source record: which
catalog file each standard group's package composition was read from, and
call out explicitly any group that was an approximation (a non-exact-match
source) or that remains unresolved for lack of any shipped catalog.

## Worked Example (Appendix B.4)

> Operator: "Generate a catalog for a minimal Slurm-only cluster on RHEL
> 10.0."

| Step | Resolution | Basis |
|------|-----------|-------|
| 1 | RHEL 10.0 | stated |
| 2 | x86_64 | default applied, confirmed |
| 3 | slurm | stated ("Slurm-only") |
| 4 | os, slurm_control_node, slurm_node | mandatory roles; login roles omitted as "minimal" |
| 5 | None (CPU-only catalog) | operator chose None when prompted |
| 6 | none | not stated; skill notes VAST is available for this stack |
| 7 | Yes — include InfiniBand | operator chose Yes when prompted |
| 8 | `slurm_custom` and `ldms` URLs outstanding | A.5 — operator-supplied by design |
| 9 | none | operator declined when asked |
| Name | slurm_cpu_rhel_10_0_x86_64 | operator selected a suggested name; custom input was also offered |

Output: three functional layers (`os_rhel_10_0_x86_64`,
`slurm_control_node_rhel_10_0_x86_64`, `slurm_node_rhel_10_0_x86_64`), each
expanded per A.3 with the conditional NVIDIA and VAST groups omitted and the
InfiniBand group included, plus an explicit report that the `slurm_custom`
and `ldms` repository URLs must be supplied before the catalog can sync. No
Slurm version is asserted anywhere, because A.6 records none. Step 4b
resolves every included group (`baseos_group`, `common_pks`,
`admin_debug_group`, `ldms_group`, `openldap_group`, `openmpi_group`,
`slurm_custom_group`, `ucx_group`, `slurm_control_node_group`,
`slurm_node_group`, `infiniband_stack_driver_groupv1`) against
`slurm_x86_64.json`, the exact stack+arch+os_version match — every group
report cites that one source file, with no approximation needed.

**Worked example — no shipped catalog available (Step 4b's gap-disclosure
path):** the same request, but every catalog under
`src/main/samples/catalogs/` has been removed or is otherwise unreadable.
Step 4b finds no instance of `slurm_control_node_group`, `slurm_node_group`,
or any other group this request needs, anywhere. The correct response is
**not** to substitute a different stack's or architecture's package
composition (e.g. reusing `service_k8s_x86_64.json`'s `baseos_group` package
set is only safe when at least one shipped instance actually exists to
verify the composition against — with zero shipped catalogs present, there
is nothing to verify against at all). Instead: report that every group's
package composition is unresolved for lack of any offline source, and ask
the operator to restore a reference catalog or supply the package lists
directly before the catalog can be assembled — do not emit a catalog with
fabricated or borrowed-from-an-unrelated-configuration package lists.

## What This Skill Does Not Do

- Editing an already-generated catalog, bulk edits across catalogs, and the
  Pre-Edit Impact & Compatibility Gate are out of scope here — see
  `ER-BSM-001-catalog-editing-skill` (not yet implemented).
- Impact Analysis and Compatibility & Dependency Analysis are out of scope
  here — see `ER-BSM-001-analysis-skills` (not yet implemented). This
  skill's connectivity layer (`shared/connectivity_layer.md`) is the shared
  foundation that Story depends on.
