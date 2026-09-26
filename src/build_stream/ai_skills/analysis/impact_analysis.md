---
name: impact-analysis
description: Standalone AI skill that traces the operational impact of a proposed package/group/layer/OS change within a single catalog — package, role, cluster, and user/workload tiers, with severity rating and a customer-facing summary. Online-preferred (local dnf/live-repo/upstream-doc lookup for every target, not gated on the master reference file), with a disclosed offline fallback. Channel-agnostic (FR-5.1).
---

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
`iproute` is not actually removable from a built node at all, because
`cloud-init`, `dracut-network`, and `mariadb-server` (already in the
catalog) require it. See R1/R2 below.

## Inputs You Must Read First

1. The target catalog's JSON (the operator's catalog file, or the one they
   name/paste). Its `catalog.functionallayer`, `catalog.groups`, and
   `catalog.packages` sections are the primary evidence.
2. `src/build_stream/ai_skills/shared/connectivity_layer.md` — the
   online/offline fallback procedure. Note its clarified trigger: fall
   back only on an actual lookup failure, never merely because a row is
   absent from one table.
3. `src/build_stream/ai_skills/analysis/trusted_source_policy.md` — the
   approved source classes, the architecture-mismatch flow, and the
   audit-logging contract for degraded-mode events.
4. `src/build_stream/ai_skills/master_reference/master_reference_file.md`
   — A.5 Package Source Defaults Table (`reponame` per package), A.6
   Pinned Version Table, and A.3 Functional-Layer Composition Table —
   consulted as described in the Procedure below, not as the first stop.

## Procedure

### Step 0 — Resolve the target to a package set (R3)

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
    package in the catalog; for each, Step 2's version-comparison lookup
    (R6) additionally checks whether the pinned version is still valid
    for the new OS version per A.1/A.8, not just whether a newer version
    exists.

Run Steps 1-3 for every package in the resolved set, then combine the
results for the report (Step 4).

### Step 1 — Look up dependencies for every package, online-first (R1)

For each package in the set, attempt sources in this order, moving to the
next only when the current one actually fails (per
`connectivity_layer.md`'s clarified trigger — "not in a table" is never
itself a reason to skip ahead):

1. **Local `dnf` metadata**, if the execution channel has shell access:
   - `dnf repoquery --whatrequires <package>` — what reverse-depends on
     it.
   - `dnf repoquery --requires <package>` — what it itself depends on
     (for the package tier, Step 3.1).
   - `dnf repoquery --info <package>` — description/summary (package
     tier) and available version (R6).
2. **The live repository named by the package's `reponame`** (A.5), if
   local `dnf` metadata was unreachable or the channel has no shell
   access but does have network access.
3. **Upstream documentation** for the package, if 1 and 2 both failed.
4. **The master reference file** (A.5/A.6/A.3) as the last resort, only
   once 1-3 have all actually failed. If used, set `disclosure=true` and
   state which of 1-3 was skipped and why (per `trusted_source_policy.md`
   step 3).

Cross-check whatever reverse dependencies were found against the
catalog's own `packages` map: only reverse-dependents that are *also
installed by this catalog* are relevant to Step 2.

If a target architecture's local repo metadata isn't available (e.g. the
catalog targets `aarch64`, only `x86_64` metadata is present locally, and
there's no online access), follow `trusted_source_policy.md`'s
architecture-mismatch flow before continuing — do not silently substitute
the other architecture's data without disclosing it.

### Step 2 — Removed from catalog vs. removed from node (R2)

For each package: if Step 1 found a reverse-dependent that is present in
this catalog's `packages` map, the package is **not actually removed by
this change** — report it as "still installed via `<X>`, `<Y>`, `<Z>`"
(name every such reverse-dependent found in the catalog). Otherwise,
report it as **effectively removed**.

This distinction gates severity (Step 5/R7): a package that's "still
installed via" something else is capped at `Low`, because the catalog
edit itself changes nothing about the built node.

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

For each package: if the catalog has a pinned version (A.6), report it.
Otherwise (or in addition, for an OS-version-change target), report the
latest version available via the Step 1 lookup (`dnf repoquery --info`,
or the live repo/upstream doc if that's what resolved it), and the newest
upstream release if that differs from the locally available one. Show the
gap plainly and state any security/feature implication the source itself
states — never invent one. For an OS-version-change target, additionally
state whether the pinned version is still valid for the new OS version
per A.1/A.8.

### Step 5 — Severity rating (R7)

Assign exactly one severity per package (or the highest across the
combined set, for a group/layer/OS target), using this rubric:

- **Critical** — the cluster cannot provision nodes or schedule jobs.
- **High** — a whole role or user-facing capability is lost.
- **Medium** — a degraded or optional feature.
- **Low** — cosmetic, or the package is still installed via a dependency
  per Step 2 (removing it from the catalog has no actual effect on the
  built node).

### Step 6 — Report, customer-summary first (R8)

Assemble the report in this fixed order:

1. **Customer-level summary and severity** — business impact stated in
   plain operational language, not internal role/group names.
2. **Actually-removed vs. still-installed-via-dependency** (Step 2).
3. **Impact tiers** — package, role, cluster, user (Step 3), each with
   both a specific scenario and its general category.
4. **Evidence table** — every claim from Step 3, with its tag (Step 3.5).
5. **Version comparison** (Step 4).
6. **Recommendations** — e.g. "no action needed, `iproute` stays
   installed via `mariadb-server`" or "removing this drops Slurm
   accounting; confirm before proceeding."
7. **Disclosures** — degraded-mode fallback (if any), `inferred` claims
   called out again in one place, and any architecture-mismatch
   substitution.

### Step 7 — No match / no fabrication

- **No group in the catalog references the package at all, and no
  reverse-dependent was found anywhere:** state that plainly — this is a
  valid answer (the package isn't used in this catalog), not an
  unresolved case. This is not a degraded-mode event by itself; only a
  failed *lookup attempt* (Step 1 exhausting all four sources without an
  answer) is degraded-mode, per `trusted_source_policy.md`.
- **Never fabricate a dependency, impact, or version claim.** If no step
  above produces evidence for a claimed relationship, do not report it —
  report the gap instead, and use the `inferred` tag only for a clearly
  labeled, reasonable operational inference, never as a stand-in for
  missing evidence.

## Worked Example (real reproduction, 2026-09-26)

> Operator: "What breaks if I remove iproute?"

Step 0: package target, resolves to `iproute` in `catalog.packages`.

Step 1 (this environment, subscribed RHEL 10.2 BaseOS/AppStream, local
`dnf` reachable — no fallback needed, `disclosure=false`):
`dnf repoquery --whatrequires iproute` returns `cloud-init`,
`dracut-network`, and `mariadb-server`. All three are present in this
catalog's `packages` map (`baseos_group` and `slurm_control_node_group`).

Step 2: **not actually removed** — still installed via `cloud-init`,
`dracut-network`, `mariadb-server`.

Step 3:
- Package tier (`repo-metadata`): provides `/usr/sbin/ip` and related
  tools — network device/route configuration.
- Role tier (`catalog`): referenced (transitively, via the packages
  above) by `baseos_group` and `slurm_control_node_group`, which appear
  in every functional layer built from this catalog.
- Cluster tier (`repo-metadata` + `inferred`): `dracut-network` uses
  `iproute` for network boot of node images; `mariadb-server` (Slurm
  accounting database) needs it for its network setup. Removing
  `iproute` from the catalog changes nothing here (Step 2).
- User tier: no direct effect — covered by "no actual removal" above.

Step 4: A.6 pins `iproute` at a specific tested version; no gap to
report since the local repo has the same version available.

Step 5: **Low** — the package is still installed via a dependency
(Step 2).

Step 6 (report order): "Removing `iproute` from the catalog has no
practical effect — it stays on every built node because `cloud-init`,
`dracut-network`, and `mariadb-server` all require it. Severity: Low." →
Step 2 detail → tiers → evidence table → version (no gap) →
recommendation ("no action needed if the goal was to reduce the node's
installed footprint; this edit won't achieve that") → no disclosures
(online lookup succeeded).

## What This Skill Does Not Do

- Cross-catalog impact tracing (out of scope, FR-3.1).
- Applying the change or updating a changelog — that is the Pre-Edit Gate
  in `ER-BSM-001-catalog-editing-skill` (not yet implemented), which calls
  this skill and then requires operator approval before any edit.
