---
name: impact-analysis
description: Traces operational impact of proposed package/group/layer/OS changes within catalogs across package, role, cluster, and workload tiers with severity ratings. Use when analyzing change impact before catalog modifications or upgrades.
---

Before starting, read `../shared/skill_scope.md` and use only this bundle's
companion skills and shared instructions.

## Purpose

Answer "what breaks if I remove/change `<target>` in `<catalog>`?" for a
target at any level — package, group, functional layer, or OS — within
**one catalog** (`ER-BSM-001-nersc-ai-skills-catalog-authoring`, FR-3.1,
AC-005/AC-009). This skill does not trace impact across separate catalogs
— that is explicitly out of scope per FR-3.1. It analyzes only; it never
edits the catalog (that remains `ER-BSM-001-catalog-editing-skill`'s
responsibility).

This skill was enhanced post-review (2026-09-26) after a real
reproduction on this environment's subscribed RHEL 10.2 BaseOS/AppStream
repos showed the original version stopped resolving `iproute` the moment
it was absent from the master reference file's A.6 table, even though a
live local `dnf` lookup answered immediately — and that lookup revealed
`iproute` may remain installed through `cloud-init`, `dracut-network`, or
`mariadb-server`. Whether that holds for a proposed change must be checked
against the surviving packages in each affected layer, as R1/R2 require.

## Inputs You Must Read First

1. The target catalog's JSON (the operator's catalog file, or the one they
   name/paste). Its `catalog.functionallayer`, `catalog.groups`, and
   `catalog.packages` sections are the primary evidence.
2. `src/build_stream/ai_skills/shared/connectivity_layer.md` — the
   online/offline fallback procedure. Note its clarified trigger: fall
   back only on an actual lookup failure, never merely because a row is
   absent from one table.
3. `src/build_stream/ai_skills/impact-analysis/references/trusted_source_policy.md`
   — the approved source classes, the architecture-mismatch flow, and the
   audit-logging contract for degraded-mode events.
4. `src/build_stream/ai_skills/catalog-selection-gate/references/master_reference_file.md`
   — A.5 Package Source Defaults Table (`reponame` per package), A.6
   Pinned Version Table, and A.3 Functional-Layer Composition Table —
   consulted as described in the Procedure below, not as the first stop.

## Procedure

### Step 0 — Resolve the target to a package set (R3)

Record the proposed operation (removal, addition, version/source change, or
OS change) and its scope before resolving the target. Distinguish deleting a
package/group globally from removing its reference in selected groups or
layers. Ask if that scope is ambiguous.

Construct a read-only before/after view of the requested change. For each
affected functional layer and its OS/architecture, expand layer -> groups ->
package keys in both views. A package-map entry is a definition, not proof
that any node installs it. Track which references and dependents survive the
whole change, including group/layer removals that remove multiple packages.
Do not mutate the catalog while analyzing it.

Determine the target's level from the operator's request:

- **Package target:** resolve the named package (e.g. "nvidia-driver") to
  its `packages` key(s) in the catalog (e.g. `nvidia_driver` and/or
  `nvidia_driver_cuda` — a package may appear under more than one key;
  check all of them). This is the package set.
- **Group target:** the package set is every key in that group's
  `components` array.
- **Functional-layer target:** expand every group the layer's
  `components` array references, then expand each group as above. The
  package set is the union.
- **OS target:** two sub-cases —
  - *Package/group change within `baseos_group`:* treat exactly like a
    group target scoped to `baseos_group`.
  - *OS-version change* (e.g. 10.0 → 10.2): the package set is every
    package reachable from an affected layer; for each, Step 4's
    version-comparison lookup (R6) checks whether the pinned version is valid
    for the new OS version per A.1/A.8, not just whether a newer version
    exists.

Run Steps 1-5 for the resolved packages and affected layers, then combine
the results for the report (Step 6). A deleted layer is a removed role;
packages remaining in other layers do not preserve that role.

### Step 1 — Look up dependencies for every package, online-first (R1)

For each package in the set, attempt sources in this order, moving to the
next only when the current one actually fails (per
`connectivity_layer.md`'s clarified trigger — "not in a table" is never
itself a reason to skip ahead):

1. **Local `dnf` metadata**, for RPM packages if the execution channel has
   shell access and metadata for the target OS/release and architecture:
   - `dnf repoquery --whatrequires <package>` — what reverse-depends on
     it.
   - `dnf repoquery --requires <package>` — what it itself depends on
     (for the package tier, Step 3.1).
   - `dnf repoquery --info <package>` — description/summary (package
     tier) and available version (R6).
   Resolve catalog keys to actual RPM names and applicable source/version
   constraints first (e.g. `mariadb_server` names RPM `mariadb-server`).
   Confirm required capabilities/providers and the dependency chain; a
   name-only reverse-dependency hit is a candidate, not proof of installation.
   For images, Python packages, Git sources, and other non-RPM artifacts,
   use their approved source metadata/documentation instead of DNF.
2. **The live repository named by the package's `reponame`** (A.5), if
   local `dnf` metadata was unreachable or the channel has no shell
   access but does have network access.
3. **Upstream documentation** for the package, if 1 and 2 both failed.
4. **The master reference file** (A.5/A.6/A.3) as the last resort, only
   once 1-3 have all actually failed. If used, set `disclosure=true` and
   state which of 1-3 was skipped and why (per `trusted_source_policy.md`
   step 3).

Cross-check reverse dependencies against the packages reachable in the
**post-change affected layer**, matching actual package identities and source
constraints rather than assuming RPM names equal catalog keys. A dependent
in another layer, an unreferenced definition, or a dependent removed by the
same change cannot establish retention. Transitive retention requires an
evidenced dependency path rooted in a package still selected in that layer.

If a target architecture's local repo metadata isn't available (e.g. the
catalog targets `aarch64`, only `x86_64` metadata is present locally, and
there's no online access), follow `trusted_source_policy.md`'s
architecture-mismatch flow before continuing — do not silently substitute
the other architecture's data without disclosing it.

### Step 2 — Determine the post-change outcome per layer (R2)

For a **removal**, classify each affected package separately for each layer:

- **Still explicitly selected:** another surviving group in the same layer
  references it. Name that group.
- **Retained via dependency:** an evidenced required-dependency path from a
  surviving package in that same layer still selects the target for the
  correct OS, architecture, and version constraints. Name the path and any
  resolver assumptions. A weak/optional dependency or an alternative provider
  does not prove retention without evidence of what the build selects.
- **Expected absent from a rebuilt node:** no explicit reference survives and
  sufficiently complete dependency/build evidence rules out implicit
  installation. This predicts a future build; a catalog edit alone does not
  uninstall packages from already deployed nodes.
- **Unresolved:** lookup failure, incomplete dependency/build evidence, or
  uncertain provider/version selection prevents a conclusion. State the gap;
  absence of a reverse-dependency result alone is not proof of removal.

For a **version/source or OS change**, assess the requested before/after
versions and constraints, compatibility, dependency resolution, and affected
operations. Remaining installed does not imply remaining compatible. Do not
apply the removal-only retention shortcut or a Low severity cap.

For an **addition**, assess compatibility and its dependency/operational
effects; do not label it as a removal.

### Step 3 — Four impact tiers (R4)

For each package (or the combined set, for a group/layer/OS target),
report all four tiers that apply. Each stated impact gives both the
specific scenario and the general category, and every claim carries an
evidence tag (R5, Step 3.5):

1. **Package tier:** what the package itself provides (from `dnf
   repoquery --info`/upstream docs), e.g. "`iproute` provides
   `/usr/sbin/ip` and related tools — network device/route/tunnel
   configuration."
2. **Role/functional-layer tier:** exactly the original blast-radius
   trace — scan `catalog.groups` for any group whose `components`
   contains the package, then scan `catalog.functionallayer` for any
   layer whose `components` contains one of those groups. Report every
   layer found, by name, with the carrying group(s).
3. **Cluster tier:** map the package's role (Step 3.1) and its
   reverse-dependents (Step 1) to cluster operations — node
   provisioning/boot, OIM-to-node connectivity, job scheduling,
   accounting, authentication — whichever categories apply. Use the
   local Omnia source tree (read-only; `trusted_source_policy.md`'s
   "local system RPM repositories" reachability, not a new source class)
   when the channel has file-system access, to find which playbook/role
   actually invokes the package, and cite that path. State plainly when
   this lookup isn't available in the current channel (browser-based),
   and rely on Step 3.1/3.2 evidence plus a labeled inference instead.
4. **User/workload tier:** job submission, MPI/GPU workloads, login —
   whichever the package's role implies, following the same evidence
   rule as tier 3.

### Step 3.5 — Evidence tags (R5)

Tag every impact claim from Step 3 with exactly one of:

- `repo-metadata` — from `dnf`/live-repo lookup.
- `upstream-doc` — from upstream documentation.
- `catalog` — from the catalog's own functional-layer/group/package
  structure (Step 2 of the original trace, and Step 2 above).
- `inferred` — a reasonable operational inference not directly stated by
  any source. Always label it as such; never present an `inferred` claim
  as if it came from a source. This keeps the skill's no-fabrication rule
  (NFR-3) intact.

### Step 4 — Version comparison (R6)

For each package: read the target catalog's actual pin first and distinguish
it from any reference pin in A.6. An RPM source's `version: ["10.2"]`
selects the OS release; it is not an RPM version pin. Report both the current
and proposed version for a version change. When no pin exists (or in
addition, for an OS-version-change target), report the
latest version available via the Step 1 lookup (`dnf repoquery --info`,
or the live repo/upstream doc if that's what resolved it), and the newest
upstream release if that differs from the locally available one. Show the
gap plainly and state any security/feature implication the source itself
states — never invent one. For an OS-version-change target, additionally
state whether the pinned version is still valid for the new OS version
per A.1/A.8.

### Step 5 — Severity rating (R7)

Assign a supported severity per package and affected layer (or the highest
across the combined set for a group/layer/OS target), using this rubric:

- **Critical** — the cluster cannot provision nodes or schedule jobs.
- **High** — a whole role or user-facing capability is lost.
- **Medium** — a degraded or optional feature.
- **Low** — cosmetic, or a removal for which Step 2 proves equivalent
  retention in every affected layer and no other operational effect is
  evidenced. Retention alone never lowers a version/source/OS change's risk.

Rate each affected layer before taking the highest evidenced severity for
the overall change. If installation or compatibility remains unresolved,
report that uncertainty; do not assign Low merely because a lookup failed.
If no severity is supportable, report `Unresolved` instead of inventing one.

### Step 6 — Report, customer-summary first (R8)

Assemble the report in this fixed order:

1. **Customer-level summary and severity** — business impact stated in
   plain operational language, not internal role/group names.
2. **Post-change outcome per layer** (Step 2), distinguishing rebuilt-node
   predictions from the unchanged state of already deployed nodes.
3. **Impact tiers** — package, role, cluster, user (Step 3), each with
   both a specific scenario and its general category.
4. **Evidence table** — every claim from Step 3, with its tag (Step 3.5).
5. **Version comparison** (Step 4).
6. **Recommendations** — tied to the affected layers and evidenced outcome,
   with unresolved dependency/compatibility questions identified explicitly.
7. **Disclosures** — degraded-mode fallback (if any), `inferred` claims
   called out again in one place, and any architecture-mismatch
   substitution.

### Step 7 — No match / no fabrication

- **No explicit reference exists in an affected layer:** report that fact.
  Only conclude the package is unused when implicit installation has also
  been ruled out. A failed or incomplete lookup remains unresolved and uses
  `trusted_source_policy.md`'s disclosure contract.
- **Never fabricate a dependency, impact, or version claim.** If no step
  above produces evidence for a claimed relationship, do not report it —
  report the gap instead, and use the `inferred` tag only for a clearly
  labeled, reasonable operational inference, never as a stand-in for
  missing evidence.

## Worked Example — removal with verified surviving dependencies

> Operator: "What breaks if I remove iproute?"

Step 0: package target, resolves to `iproute` in `catalog.packages`.

For this example, assume matching RHEL 10.2/architecture metadata confirms
that `cloud-init`, `dracut-network`, and `mariadb-server` require `iproute`.
Map those names to `cloud_init`, `dracut_network`, and `mariadb_server`.
The requested edit removes only the `iproute` reference from `baseos_group`.
The post-change layer expansion shows `cloud_init` and `dracut_network`
remain in every affected layer through `baseos_group`; `mariadb_server`
remains only in the Slurm control layer. Verify these assumptions against
the actual target catalog and metadata before reporting this result.

Step 2: **retained via dependency** in each affected rebuilt layer through
the surviving base-OS dependencies. Cite `mariadb-server` only for the
control layer, not as evidence for compute or login nodes.

Step 3:
- Package tier (`repo-metadata`): provides `/usr/sbin/ip` and related
  tools — network device/route configuration.
- Role tier (`catalog`): the surviving base-OS dependencies are selected
  in each affected layer; the database package is control-layer-only.
- Cluster tier (`inferred`): `dracut-network` uses
  `iproute` for network boot of node images; `mariadb-server` (Slurm
  accounting database) needs it for its network setup. Removing
  `iproute` from the catalog changes nothing here (Step 2).
- User tier: no direct effect — covered by "no actual removal" above.

Step 4: neither A.6 nor this sample's `iproute` entry pins an RPM version.
Its source `version: ["10.2"]` is the OS selector. Report available RPM
versions only if an actual metadata lookup supplies them.

Step 5: **Low** — the package is still installed via a dependency
(Step 2).

Step 6 (report order): "Removing `iproute` from the catalog has no
practical effect on the affected rebuilt layers under the verified
dependency selection: the surviving base-OS packages still require it.
Severity: Low." →
Step 2 detail → tiers → evidence table → version (unpinned) →
recommendation ("no action needed if the goal was to reduce the node's
installed footprint; this edit won't achieve that") → no disclosures
(only when the matching metadata lookup actually succeeded).

**Group removal:** if the same change removes the dependent and target
together from a layer, the old dependency edge does not prove retention.
Recompute from the surviving layer roots and report absence or uncertainty
according to the available evidence.

**Version change:** a retained NVIDIA driver can still become incompatible
with CUDA or the target OS. Assess that change on its own evidence; never
cap it at Low just because another package requires the driver.

## What This Skill Does Not Do

- Cross-catalog impact tracing (out of scope, FR-3.1).
- Applying the change or updating a changelog — that is the Pre-Edit Gate
  in `ER-BSM-001-catalog-editing-skill` (not yet implemented), which calls
  this skill and then requires operator approval before any edit.
