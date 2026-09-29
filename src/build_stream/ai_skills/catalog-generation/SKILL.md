---
name: catalog-generation
description: Generates Omnia catalogs from operator-described roles, OS families/versions, architectures, and packages. Use when creating single-platform, hybrid-OS, or mixed-stack catalogs from verified catalog and consumer support.
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
generation. Discover catalogs recursively: both the older `<version>/` layout
and the newer `<family>/<version>/` plus `hybrid/` layout may be present.
Default to this checkout. An operator may explicitly designate another catalog
root/worktree as reference data; record its path and revision, distinguish it
from the active checkout, and use only its catalog
data as authorized. Never load companion skills from that root, silently switch
validation/runtime checkouts, or search other checkouts for missing inputs.
The storage and role-architecture rules below refine the older reference capture:
PowerScale NFS is distinct from CSI, existing storage is asked rather than assumed,
and the Kubernetes architecture restriction applies to its roles, not every role
in a mixed cluster. OS selection is per role, not a single catalog-wide value.
Leave unrelated reference-table reconciliation deferred.

### Hybrid scope and support evidence

Distinguish three independent choices: mixed stack (Slurm + Kubernetes), mixed
architecture, and hybrid OS (multiple family/version pairs). A request may combine
them. Ask for OS family and version, not just a version number, and preserve all
requested families in the working record even when some need more evidence.

Hybrid examples mixing **RHEL 10.2 and RHEL 10.0** demonstrate multi-version
role mapping, not Ubuntu/Rocky/SLES support. For every additional
family/version/architecture, require concrete base-group/package definitions,
supported package types and sources, and evidence that the active catalog
consumers preserve that tuple through repository resolution and image building.
Do not translate RPM names into another distribution's package names, reuse RHEL
repositories for another family, or treat a free-form schema `os` string as proof
of runtime support. Missing evidence leaves that part unresolved; do not drop it
or label a reduced RHEL-only result as the complete requested hybrid catalog.

Known limits in the inspected checkout: the catalog schema accepts no `deb`
package type, and `src/image_build_manager/plugins/modules/parse_catalog.py`
returns one `cluster_os_type` and indexes base packages by version rather than
family/version. Recheck these contracts in the active checkout before accepting
multiple families; a schema-valid multi-family JSON alone is insufficient.
Explain required consumer/package-provider work if those limits still apply.
This skill must not modify runtime code or promise deployment support it lacks.

## Step 1 — Normalize the request and ask only missing questions

Start briefly: explain that you will resolve missing cluster details, confirm
the configuration, then generate and validate the catalog. Extract supplied
answers into the seven domains before asking anything:

| Domain | Resolve | Defaults and dependencies |
|---|---|---|
| Platform | OS family/version/architecture tuples | Resolve each role's platform; propose x86_64 only when deferred and supported for that family/version |
| Software Stack | Slurm, Kubernetes, or mixed | No default; mixed means both stacks with explicit role assignments |
| Compute | Role-to-platform assignments, NVIDIA or None | Derive mandatory roles; apply the OS and architecture rules below |
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
rules. A complete hybrid request needs explicit `(role, os_family, os_version,
architecture)` assignments, not a cross-product of every role and platform.

### OS configuration prompt — explicitly offer hybrid

When OS selection is unanswered, ask "Which OS configuration do you need?"
Do not present supported versions as an implicitly single-choice list. When
the reference data supports RHEL 10.0 and RHEL 10.2, explicitly offer:

- RHEL 10.0 only
- RHEL 10.2 only
- Both RHEL 10.0 and 10.2 — hybrid

Also invite free-text input: "For another OS family/version or combination,
specify what you need; support needs verification." This is a request for
requirements, not a claim that other families are supported. Adapt the named
versions to the available reference data; keep the explicit hybrid choice
when multiple supported versions are available.

Accept "both", "hybrid", or an explicit list of versions without making the
operator pick just one. If more than two versions are offered, clarify which
ones "both" means. Reuse an already supplied single-OS or hybrid selection.
Choosing hybrid records intent, not proof that every role/platform combination
is supported; apply the hybrid evidence checks before assembly.

For hybrid, next resolve which selected OS each controller and compute pool
uses, then any requested login/compiler and Kubernetes roles. If the stack is
unknown, resolve it first so only applicable roles are asked about. For Slurm,
offer "controller on RHEL 10.2, compute on RHEL 10.0" as an example, not an
automatic assignment. Reuse supplied role mappings and apply the defaults and
compatibility checks below to the missing OS/architecture assignments.

### Compute roles and platform assignments

- Slurm requires `os`, `slurm_control_node`, and `slurm_node`; Kubernetes requires
  `os`, `service_kube_control_plane`, and `service_kube_node`. Mixed requires both
  sets. `os` covers every selected `(family, version, architecture)` tuple.
- With one platform tuple, assign standard roles to it subject to compatibility.
  With multiple tuples, ask which family/version/architecture each controller,
  compute pool, login role and Kubernetes role uses. Controller platform is
  independent of compute. Kubernetes roles require supported OS/version evidence
  and remain x86_64 in the current reference set; mixed clusters may have aarch64
  Slurm compute. Do not infer role placement from all sources listed on a package.
- When requested, `login_compiler_node` must match the Slurm compute architecture
  set. With both compute architectures, provide a matching compiler layer for
  each. Also propose its associated compute pool's OS family/version and confirm
  that pairing. A different compiler OS needs explicit compatible build/runtime
  evidence and operator confirmation; never infer cross-compilation or ABI
  compatibility from matching architecture alone.
- When requested, `login_node` defaults to the compute architecture set, not the
  controller architecture. Disclose this default; allow an explicit override to
  another supported platform architecture. Also default its OS family/version to
  its associated compute pool, while permitting a supported explicit override.
  For multiple pools, ask which it serves instead of choosing the first tuple.
  Neither login role becomes mandatory.

Example: controller x86_64, compute aarch64 → compiler aarch64; login defaults to
aarch64 but the operator can change it to x86_64. Kubernetes stays on x86_64.

The `slurm_service_k8s_hybrid_10_2_10_0_combined.json` catalog maps roles as follows
(example, not defaults; locate it under the approved catalog root):

| Role | OS family/version | Architecture | Base-group key |
|---|---|---|---|
| Slurm controller | RHEL 10.2 | x86_64 | `baseos_group_10.2` |
| Kubernetes control-plane and worker | RHEL 10.2 | x86_64 | `baseos_group_10.2` |
| Slurm compute | RHEL 10.0 | aarch64 | `baseos_group_10.0` |
| Login/compiler | RHEL 10.0 | aarch64 | `baseos_group_10.0` |
| Login | RHEL 10.0 | x86_64 | `baseos_group_10.0` |

It has three `os` layers: RHEL 10.2/x86_64, RHEL 10.0/x86_64 and
RHEL 10.0/aarch64. Its login architecture is an explicit departure from the
compute default. Single-architecture hybrid variants keep controller on 10.2 and
compute/login/compiler on 10.0, all on the chosen architecture. The `_no_vast`
variants omit VAST without changing those platform assignments. Read the selected
example's actual layers/groups, not just its filename or description.

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
Apply both hardware choices per eligible platform tuple: a NVIDIA/InfiniBand
group observed on RHEL is not evidence that its packages support another family
or version. If one selected tuple lacks drivers, report that tuple rather than
silently enabling the feature on only the supported subset.

### Catalog identity

Reuse a supplied catalog name. Otherwise suggest two or three names reflecting
the selected OS/stack/architecture, and offer custom input in the same prompt.
For example: `slurm_cpu_rhel_10_2_aarch64`, `hpc_slurm_rhel_10_2_aarch64`, or a
custom name. Do not imply GPU/InfiniBand support when omitted.
For hybrid requests, suggestions and the description must reflect all selected
families/versions; for example `slurm_hybrid_rhel_10_2_10_0` when accurate.

Accept schema-valid display names with spaces. Propose a separate identifier and
filename stem by lowercasing, replacing runs outside `[a-z0-9_-]` with `_`, and
trimming leading/trailing `_`/`-`; use `catalog` if empty. Show this mapping.
Propose version `1.0.0` for a new catalog and a description derived from the
confirmed configuration. Honor explicit metadata and paths. For a single OS
family/version (even with multiple architectures), follow the active checkout's existing `<family>/<version>/` or
legacy `<version>/` directory layout. For multiple family/version pairs, propose
`src/main/samples/catalogs/hybrid/<identifier>.json` in the active checkout, or an
operator-chosen path. Do not publish into a read-only reference worktree. Confirm
new destination directories and resolve filename collisions; silence does not
accept a name or other default.

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
`device_mapper_multipath` for a RHEL PowerVault controller. These keys are RHEL
reference definitions, not universal package names: other families require their
own verified NFS/iSCSI/client definitions and driver compatibility. Do not invent a storage
group just to represent runtime configuration. Report required exports, mount
targets, and deployment settings without collecting secrets or editing them.

## Step 3 — Cross-domain preflight and confirmation

Review the working record against the reference data and the rules in this skill:

| Relationship | Check before assembly |
|---|---|
| Platform ↔ Stack | Verify each family/version/architecture tuple against catalog data and active consumers; Kubernetes roles remain x86_64 in the current reference set |
| Stack ↔ Compute | Mandatory roles present; optional/custom roles explicit; no implicit role/platform cross-product |
| Compute ↔ Login/compiler | Compiler architecture matches its compute pool, OS compatibility verified; login defaults to compute but explicit overrides are preserved |
| Compute ↔ GPU | NVIDIA only on eligible roles; None conflicts with custom NVIDIA driver/CUDA requests |
| Storage ↔ Role/access method | PowerVault controller use; VAST on applicable compute/login roles; plain NFS distinct from Kubernetes CSI |
| Network ↔ Role/architecture | InfiniBand only on applicable roles with matching driver sources; No must not be undone by a custom package |
| Packages ↔ Platform/Stack | Source coverage for consuming architectures/OS and compatible stack version pins |

This is an instruction-driven review, not an executable preflight. For a conflict,
state the affected domain/field, requested value, violated rule, reason, and
supported alternatives. Ask the operator to resolve it; do not silently switch
choices or drop an architecture. If evidence is missing, mark the item unresolved.

Restate all seven domains, including a role/family/version/architecture mapping,
reference-root provenance, storage purpose
and access method, defaults, custom content, catalog identity, and output path.
Ask for confirmation once the configuration is complete. Only after approval
begin assembly. Later changes invalidate confirmation
and require rechecking affected dependencies and reconfirming the changed record.

Without shell access, perform the same interview and review, but disclose that
schema validation cannot run. Any resulting JSON remains an unvalidated draft.

## Step 4 — Expand approved assignments and resolve group membership

Emit exactly one layer for each approved `(role, os_family, os_version,
architecture)` assignment, using the verified consumer-compatible naming pattern
`<role>_<os_family>_<os_version_with_underscores>_<architecture>` (RHEL examples:
`slurm_control_node_rhel_10_2_x86_64`, `slurm_node_rhel_10_0_aarch64`). Emit `os`
for every selected platform tuple. Do not collapse two versions of a role or
invent layers for unused combinations.

### Base groups and hybrid package identity

- Every layer references **exactly one** `type: base_os` group whose `os` and
  `os_version` match that layer's confirmed tuple. Treat those fields as metadata,
  not something to guess from the group key or catalog name.
- Single-OS references use `baseos_group`. The RHEL hybrid examples instead use
  the dictionary keys `baseos_group_10.2` and `baseos_group_10.0`, while each
  group's internal `name` remains `baseos_group`. Components refer to dictionary
  keys; never collapse the two groups because their internal names match.
- Keep one separate base definition per family/version (and per architecture
  when actual package composition requires it). Reuse verified keys. For a new,
  otherwise supported cross-family combination, disambiguate colliding keys with
  family and version, preserve the `baseos_group` prefix/type, and confirm consumer
  compatibility. The same version string in two families is not the same base OS.
- Shared groups/package keys may be reused only when their definitions and
  applicability really agree. A package's global `version`, image `tag`, type
  and name cannot represent conflicting platform-specific definitions. In that
  case keep distinct keys and split the affected groups/references; do not use
  last-writer-wins or treat OS source selectors as package-version overrides.
- The hybrid RHEL `systemd` entry demonstrates separate x86_64/aarch64 source
  records with `name: rhel` and `version: ["10.2", "10.0"]`. Merge version lists
  only for otherwise identical source records with verified availability. Keep
  different OS families, architectures, repository names and URLs separate.
  Never add a family/version to a source merely to satisfy a selected layer.

Read A.3's always groups for the matching RHEL role and substitute the correct
base-group key. Other families require their own verified composition; do not
reuse the RHEL A.3 package set wholesale. Apply these conditional groups only
where the selected tuple has verified driver/package support:

| Group | Required selection | Eligible roles |
|---|---|---|
| `nvidia_stack_driver_groupv1` | NVIDIA | Slurm compute, login/compiler |
| `infiniband_stack_driver_groupv1` | InfiniBand Yes | Slurm controller/compute/login/compiler and Kubernetes control-plane/worker |
| `vast_stack_driver_groupv1` | VAST job storage | Slurm compute, login, login/compiler |
| `powerscale_csi_group` | Explicit PowerScale CSI | Kubernetes control-plane/worker only |

Do not attach these groups to the standalone `os` layer. PowerScale NFS does not
satisfy the CSI selection even though the older A.3 capture says `storage=PowerScale`.

For each standard group, search the approved catalog root recursively for that
exact key (`rg -l` or direct file reads). Read actual component lists, not just
the group's name; for base groups also match `type`, `os`, and `os_version`:

1. If all matching instances agree, reuse that package-key set.
2. If they differ, use the instance matching OS family/version, stack and assigned architectures.
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
reference entries. Record custom role platform tuples and group keys before
confirmation. Use the same layer-name pattern, avoid standard-role collisions,
and use non-colliding snake_case group keys ending in `_group` (or
`_stack_driver_groupv1` for driver groups). Include the appropriate platform's
base-OS group in every custom layer. The standard conditional groups retain their defined role eligibility;
do not invent eligibility for a custom role. Resolve custom packages as in Step 5.

## Step 5 — Resolve package definitions and sources

Use selected reference definitions and fixed A.5/A.6 values only where they match
the consuming family/version/architecture. Do not inherit RHEL defaults for a
different family or assume 10.0 sources cover 10.2 without evidence.
For metadata not already fixed, or an explicit source/version override, use the
shared connectivity procedure and disclose fallback. Do not silently upgrade
pinned packages. Preserve valid unpinned RPM definitions: package `version` is
not universally required, and `sources[].version` for RHEL is the OS selector,
not the RPM version. Images use their schema-required `tag`.

Every node package must have a matching source for each consuming layer's
architecture, OS family and version (or an applicable `noarch` source). `noarch`
relaxes architecture only, not OS-family/version compatibility. Shared image-builder
artifacts are checked against their evidenced build-platform support instead.
Do not add `deb` or another unsupported package type to get a new OS through the
current schema, or mislabel such a package as `rpm`. Unsupported providers remain
an explicit prerequisite outside this skill's instruction-only scope.
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
2. Layer names are unique and exactly cover approved role/family/version/architecture assignments,
   including mandatory roles. Compiler/login assignments follow the above rules.
3. Mandatory role groups from the applicable reference are present, with exactly
   one matching base-OS group per layer. Check dictionary keys, not just group
   `name`. Each conditional group is present only where
   selected and applicable, with its actual shipped package composition—not an
   empty placeholder. Plain NFS/PowerVault do not invent new storage groups.
4. Every node package has an applicable source for its consuming layer's OS family,
   version and architecture, or an applicable `noarch` source. Check the OS selector separately
   from package version. Shared base groups may contain the architecture-specific
   build artifacts `docker_io/dellhpcomniaaisolution/image_build_el10` and
   `docker_io/dellhpcomniaaisolution/image_build_aarch64`: check each against its
   selected build platform instead of requiring both on every node. They are not
   evidence for a new OS family. Do not extend this exception without evidence.
5. GPU=None and InfiniBand=No have not been undone by driver packages placed in
   another group. PowerScale NFS has not pulled in PowerScale CSI artifacts. Trace
   surviving dependencies before removing packages: generic utilities such as Helm
   may be explicitly needed elsewhere even when CSI is not selected.
6. NFS/iSCSI client packages and requested additions exist on their intended
   layers with appropriate sources. No dangling references or unused groups/packages
   remain after pruning. No requested package/group was silently omitted.
7. Multi-family output retains OS identity through the active consumer path;
   neither schema success nor a matching filename establishes that. Report an
   unsupported runtime contract separately and keep such output a blocked draft.

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
