---
name: catalog-generation
description: Generates schema-valid Omnia catalogs from operator-described functional groups, base OS, and package lists. Use when creating new catalogs for cluster configurations (Slurm, Kubernetes, or mixed-stack deployments).
---

Before starting, read `../shared/skill_scope.md` and use only this bundle's
companion skills and shared instructions. This skill generates new catalogs;
editing, bulk changes, and general impact analysis belong to the corresponding
skills in this same bundle. Do not commit or push as part of generation.
Keep this workflow instruction-driven: do not create Python helpers, scripts,
schemas, or rule files. Reuse only the existing catalog validation command below.

## Required inputs

Read before making selections:

- `../catalog-selection-gate/SKILL.md` and its
  `references/master_reference_file.md`: supported selections and Appendix A
  role/group/source tables. Use the selection gate when offering choices.
- `../shared/connectivity_layer.md`: approved source lookup and fallback disclosure.
- `../shared/working_directory.md`: invocation-specific draft workspace.
- `src/repo_manager/schemas/catalog_schema.json`: the existing catalog schema.

The shipped catalogs under `src/main/samples/catalogs/` are authoritative for
concrete group membership and package definitions. The reference tables are a
snapshot, not a substitute for those files. Recheck relevant rows when the
checkout differs from the capture; do not repair unrelated reference data during
generation. Do not search another checkout or installed skill for missing inputs.
The storage and role-architecture rules below refine the older reference capture:
PowerScale NFS is distinct from CSI, existing storage is asked rather than assumed,
and the Kubernetes architecture restriction applies to its roles, not every role
in a mixed cluster. Leave unrelated reference-table reconciliation deferred.

## Step 1 — Normalize the request and ask only missing questions

Start briefly: explain that you will resolve missing cluster details, confirm
the configuration, then generate and validate the catalog. Extract supplied
answers into the seven domains before asking anything:

| Domain | Resolve | Defaults and dependencies |
|---|---|---|
| Platform | RHEL version and architecture set | OS version needs a choice; propose x86_64 only when architecture is deferred |
| Software Stack | Slurm, Kubernetes, or mixed | No default; mixed means both stacks with explicit role assignments |
| Compute | Roles, role-to-architecture assignments, NVIDIA or None | Derive mandatory roles; apply the architecture rules below |
| Storage | Existing controller/job storage and Kubernetes access methods | No assumed VAST or CSI; ask about the actual environment |
| Network | Include InfiniBand: Yes / No | Propose Yes only when explicitly deferred; No does not mean Ethernet-only |
| Packages and Sources | Additional packages and their target roles, custom roles, source overrides | Reuse supplied answers; propose no additions/overrides only when deferred |
| Output | Display name, identifier, version, description, destination | Reuse explicit values; offer names and disclose metadata defaults |

Keep a working selection record in the conversation, organized by these domains;
it is not a new schema or fields added to the catalog. Distinguish explicit
choices, derived values, defaults, conflicts, and unanswered questions.
Ask one missing decision at a time; accept answers that resolve several domains. Do not ask again
for an already supplied choice, including additional packages, role assignments,
or a catalog name. "Minimal" alone does not answer storage or hardware questions.
An explicit "no additional packages" does answer that question. Silence is not
consent to a default. Disclose applied defaults and include them in confirmation.

Mandatory roles are derived from the stack and disclosed. Optional login roles
are included only when requested; their architecture still follows the Compute
rules. A complete multi-architecture request needs explicit role assignments,
not every role multiplied by every architecture.

### Compute roles and architecture

- Slurm requires `os`, `slurm_control_node`, and `slurm_node`; Kubernetes requires
  `os`, `service_kube_control_plane`, and `service_kube_node`. Mixed requires both
  sets. `os` covers every selected architecture.
- With one architecture, assign standard roles to it subject to compatibility.
  With multiple architectures, ask which run Slurm controllers and computes;
  controller architecture is independent of compute. Kubernetes roles must be
  x86_64, but a mixed cluster may have aarch64 Slurm compute.
- When requested, `login_compiler_node` must match the Slurm compute architecture
  set. With both compute architectures, provide a matching compiler layer for
  each. A mismatch requires clarification, not an implicit cross-compilation mode.
- When requested, `login_node` defaults to the compute architecture set, not the
  controller architecture. Disclose this default; allow an explicit override to
  another supported platform architecture. Neither login role becomes mandatory.

Example: controller x86_64, compute aarch64 → compiler aarch64; login defaults to
aarch64 but the operator can change it to x86_64. Kubernetes stays on x86_64.

### Hardware prompts

When unanswered, ask "GPU support: NVIDIA, or None (CPU-only catalog, without
NVIDIA GPU driver/CUDA groups)?" None describes the configured software, not
whether the machines physically contain GPUs. Propose None only when the
operator explicitly defers. NVIDIA applies only to eligible Slurm compute and
login/compiler roles. If no selected role is eligible, explain the conflict;
do not attach GPU groups to controller, login-only, OS, or Kubernetes roles.

When unanswered, ask "Include InfiniBand support? Yes / No." Yes includes its
group on eligible roles; No omits it without asserting which other network
interfaces the site uses. Do not present Ethernet as a separate choice.

### Catalog identity

Reuse a supplied catalog name. Otherwise suggest two or three names reflecting
the selected OS/stack/architecture, and offer custom input in the same prompt.
For example: `slurm_cpu_rhel_10_2_aarch64`, `hpc_slurm_rhel_10_2_aarch64`, or a
custom name. Do not imply GPU/InfiniBand support when omitted.

Accept schema-valid display names with spaces. Propose a separate identifier and
filename stem by lowercasing, replacing runs outside `[a-z0-9_-]` with `_`, and
trimming leading/trailing `_`/`-`; use `catalog` if empty. Show this mapping.
Propose version `1.0.0` for a new catalog and a description derived from the
confirmed configuration. Honor explicit metadata and paths. The default path is
`src/main/samples/catalogs/<os_version>/<identifier>.json`. Resolve filename
collisions before confirmation; silence does not accept a name or other default.

## Step 2 — Resolve storage by environment and purpose

If not already answered, ask: "What storage is available in your cluster
environment?" Then resolve only missing purpose/access details:

- Slurm controller: PowerVault when present, otherwise explicitly no PowerVault.
- Job/compute storage: VAST, Generic NFS, and/or PowerScale NFS. Multiple existing
  backends may coexist. Do not automatically select VAST or treat PowerVault as
  an alternative to job storage. If no job storage is selected, disclose the
  outstanding shared-storage requirement before deployment.
- Kubernetes: record any Generic NFS/PowerScale NFS backend separately, then ask
  whether PowerScale CSI is required. Do not infer CSI from owning a PowerScale
  array or using its NFS exports. Plain NFS remains available without CSI.

PowerScale NFS and Generic NFS use existing base NFS client packages and runtime
mount configuration; neither adds a PowerScale CSI group. PowerVault uses existing
iSCSI/multipath packages and controller-targeted runtime configuration, not a new
catalog group. VAST adds its client group on applicable Slurm compute/login roles.
CSI adds `powerscale_csi_group` only on Kubernetes roles and still needs explicit
Orchestrator enablement. Do not change deployment files during catalog generation.

These choices describe storage use, not exclusive vendors: PowerVault controller
storage and VAST/NFS job storage can coexist. "No PowerVault" does not mean the
controller has no disks or mounts. Generic mounts can also target controllers
and Kubernetes; the catalog-generation policy does not restrict the mount engine.

Derive runtime behavior from this checkout's
`src/orchestrator/input/storage_config.yml`,
`src/orchestrator/roles/mount_config/tasks/process_single_mount.yml`,
`src/orchestrator/roles/slurm_config/tasks/create_slurm_dir.yml`, and
`src/orchestrator/roles/k8s_config/README.md`:
plain NFS uses vendor-neutral mounts, absent VAST selection reuses Slurm NFS
storage, and CSI has separate enablement. Retain/check base `nfs_utils` and
`nfs4_acl_tools` for NFS clients and existing `iscsi_initiator_utils` and
`device_mapper_multipath` for a PowerVault controller. Do not invent a storage
group just to represent runtime configuration. Report required exports, mount
targets, and deployment settings without collecting secrets or editing them.

## Step 3 — Cross-domain preflight and confirmation

Review the working record against the reference data and the rules in this skill:

| Relationship | Check before assembly |
|---|---|
| Platform ↔ Stack | Supported OS and architectures; Kubernetes roles x86_64; mixed Slurm roles may be aarch64 |
| Stack ↔ Compute | Mandatory roles present; optional/custom roles explicit; no implicit role/architecture cross-product |
| Compute ↔ Login/compiler | Compiler matches compute; login defaults to compute but explicit overrides are preserved |
| Compute ↔ GPU | NVIDIA only on eligible roles; None conflicts with custom NVIDIA driver/CUDA requests |
| Storage ↔ Role/access method | PowerVault controller use; VAST on applicable compute/login roles; plain NFS distinct from Kubernetes CSI |
| Network ↔ Role/architecture | InfiniBand only on applicable roles with matching driver sources; No must not be undone by a custom package |
| Packages ↔ Platform/Stack | Source coverage for consuming architectures/OS and compatible stack version pins |

This is an instruction-driven review, not an executable preflight. For a conflict,
state the affected domain/field, requested value, violated rule, reason, and
supported alternatives. Ask the operator to resolve it; do not silently switch
choices or drop an architecture. If evidence is missing, mark the item unresolved.

Restate all seven domains, including role/architecture mappings, storage purpose
and access method, defaults, custom content, catalog identity, and output path.
Ask for confirmation once the configuration is complete. Only after approval
begin assembly. Later changes invalidate confirmation
and require rechecking affected dependencies and reconfirming the changed record.

Without shell access, perform the same interview and review, but disclose that
schema validation cannot run. Any resulting JSON remains an unvalidated draft.

## Step 4 — Expand approved assignments and resolve group membership

Emit exactly one layer for each approved `(role, architecture)` pair, named
`<role>_rhel_<os_version_with_underscores>_<architecture>`. Emit `os` for every
selected architecture; do not duplicate layer names. Read A.3's always groups
and apply these conditional group rules; preserve the fixed `baseos_group` key:

| Group | Required selection | Eligible roles |
|---|---|---|
| `nvidia_stack_driver_groupv1` | NVIDIA | Slurm compute, login/compiler |
| `infiniband_stack_driver_groupv1` | InfiniBand Yes | Slurm controller/compute/login/compiler and Kubernetes control-plane/worker |
| `vast_stack_driver_groupv1` | VAST job storage | Slurm compute, login, login/compiler |
| `powerscale_csi_group` | Explicit PowerScale CSI | Kubernetes control-plane/worker only |

Do not attach these groups to the standalone `os` layer. PowerScale NFS does not
satisfy the CSI selection even though the older A.3 capture says `storage=PowerScale`.

For each standard group, search shipped catalogs for that exact key (`rg -l`
or direct file reads). Read actual component lists, not just the group's name:

1. If all matching instances agree, reuse that package-key set.
2. If they differ, use the instance matching OS, stack and assigned architectures.
   For mixed/multi-architecture generation inspect the combined catalogs. Merge
   compatible source entries by package key; do not overwrite one architecture
   with another. Conflicting versions or definitions require resolution, not a
   guessed union. Keep architecture-specific image-builder artifacts for their
   selected build architectures; do not invent cross-architecture sources.
3. If no exact instance exists, establish compatible composition from available
   definitions and disclose its provenance; a "closest" catalog alone is not
   evidence. Missing group/package definitions remain unresolved. Ask for the
   missing reference or an explicit operator-defined package list.

Record the source catalog for each group and any departures from its composition.
Do not fabricate packages when shipped references are unavailable.

For additional packages, preserve the requested target roles. If modifying a
shared group would add packages to unrequested roles, use an operator-defined
group attached only to the requested layers. Record each additional package key
and its target roles in the confirmed Packages and Sources record.

Custom roles/groups are explicitly operator-defined, not claimed as supported
reference entries. Record custom role architectures and group keys before
confirmation. Use the same layer-name pattern, avoid standard-role collisions,
and use non-colliding snake_case group keys ending in `_group` (or
`_stack_driver_groupv1` for driver groups). Include `baseos_group` in every custom
layer. The standard conditional groups retain their defined role eligibility;
do not invent eligibility for a custom role. Resolve custom packages as in Step 5.

## Step 5 — Resolve package definitions and sources

Use the selected shipped definitions and fixed A.5/A.6 values where available.
For metadata not already fixed, or an explicit source/version override, use the
shared connectivity procedure and disclose fallback. Do not silently upgrade
pinned packages. Preserve valid unpinned RPM definitions: package `version` is
not universally required, and `sources[].version` for RHEL is the OS selector,
not the RPM version. Images use their schema-required `tag`.

Every node package must have a matching source for each consuming layer's
architecture and OS (or an applicable `noarch` source). Shared architecture-specific
image-builder artifacts are checked against their build architecture instead.
Check stack version co-requisites against A.8 and review explicit source overrides;
schema validation alone does not prove upstream version compatibility.

Operator-supplied repositories such as `slurm_custom`, `ldms` and `vast` have no
default URL by design. Preserve `reponame`; report missing URL mappings before
sync instead of inventing them. That action is distinct from an unresolved package.

If a requested package/group cannot be resolved, retain it in the record's
unresolved-items list and disclose a partial draft. Never remove the request just to
pass validation or insert placeholders into the catalog. A schema-valid subset
is not a complete deliverable.

## Step 6 — Assemble and validate before publication

Assemble the confirmed identity, `schema_version: 2`, layers, groups and packages
in `$WORKDIR/draft_catalog.json`. Follow surviving layer → group → package
references before pruning unused groups/packages; never delete a dependency just
because one group was excluded. Custom requests conflicting with GPU=None or
InfiniBand=No need clarification, not silent reinsertion of driver packages.

Run Omnia's existing catalog schema/business-rule validator; do not write a new
validation helper or generate a script to perform these checks:

```bash
python3 src/repo_manager/plugins/module_utils/catalog/catalog_manager.py \
  validate --catalog "$WORKDIR/draft_catalog.json" \
  --schema src/repo_manager/schemas/catalog_schema.json
```

Require exit code 0, no `[ERROR]` lines, and evidence that schema validation ran.
A missing `jsonschema` library or unreadable/missing schema blocks validation;
do not omit `--schema` to bypass it.

Then inspect the actual draft against the confirmed record. The existing validator
does **not** enforce all of the following; this is a separate model-performed review:

1. Identity matches the confirmed name/identifier/version/description; schema
   version is 2. The publication destination matches the confirmed path.
2. Layer names are unique and exactly cover approved role/architecture pairs,
   including mandatory roles. Compiler/login assignments follow the above rules.
3. Mandatory A.3 groups are present. Each conditional group is present only where
   selected and applicable, with its actual shipped package composition—not an
   empty placeholder. Plain NFS/PowerVault do not invent new storage groups.
4. Every node package has an applicable source for its consuming layer's OS and
   architecture, or an applicable `noarch` source. Check the OS selector separately
   from package version. Shared base groups may contain the architecture-specific
   build artifacts `docker_io/dellhpcomniaaisolution/image_build_el10` and
   `docker_io/dellhpcomniaaisolution/image_build_aarch64`: check each against its
   selected build architecture instead of requiring both on every node. Do not
   extend this exception to other packages without evidence.
5. GPU=None and InfiniBand=No have not been undone by driver packages placed in
   another group. PowerScale NFS has not pulled in PowerScale CSI artifacts. Trace
   surviving dependencies before removing packages: generic utilities such as Helm
   may be explicitly needed elsewhere even when CSI is not selected.
6. NFS/iSCSI client packages and requested additions exist on their intended
   layers with appropriate sources. No dangling references or unused groups/packages
   remain after pruning. No requested package/group was silently omitted.

Report schema-validation results separately from this selection review. Do not
claim these semantic checks ran automatically. Any unresolved or failed check
leaves a draft; explain the affected selection and resolve it without changing
confirmed intent. Neither review proves live repository access or readiness to sync.

After all checks pass, publish to the confirmed output path without overwriting
an existing catalog. Honor explicit paths; do not interpret display names as shell
commands. Without shell access return JSON labelled **unvalidated draft**, never
claim executable validation passed. Clean only this invocation's scratch workspace
per the shared working-directory procedure, preserving requested deliverables.

## Step 7 — Completion summary

Report the output path/name, the seven-domain configuration, actual validation
status, unresolved items (if any), and per-group source provenance. Distinguish
catalog-managed groups from runtime-only mount/PowerVault configuration. For CSI,
remind the operator that catalog artifacts do not set `enable_powerscale_csi`.
List referenced repository names needing mappings in `repo_manager_config.yml`
before sync. Do not call an unresolved or unvalidated draft a completed catalog.
