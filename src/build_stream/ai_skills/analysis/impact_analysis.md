---
name: impact-analysis
description: Standalone AI skill that traces the dependency relationships across functional layers within a single catalog to report the blast radius of a proposed package removal or change. Online-preferred with a disclosed offline fallback. Channel-agnostic (FR-5.1).
---

## Purpose

Answer "what breaks if I remove/change `<package>` in `<catalog or functional
group>`?" by tracing functional-layer references within **one catalog**
(`ER-BSM-001-nersc-ai-skills-catalog-authoring`, FR-3.1, AC-005/AC-009). This
skill does not trace dependencies across separate catalogs — that is
explicitly out of scope per FR-3.1.

## Inputs You Must Read First

1. The target catalog's JSON (the operator's catalog file, or the one they
   name/paste). Its `catalog.functionallayer`, `catalog.groups`, and
   `catalog.packages` sections are the primary evidence.
2. `src/build_stream/ai_skills/shared/connectivity_layer.md` — the
   online/offline fallback procedure for the transitive-dependency lookup.
3. `src/build_stream/ai_skills/analysis/trusted_source_policy.md` — the
   approved source classes and audit-logging contract for degraded-mode
   events.
4. `src/build_stream/ai_skills/master_reference/master_reference_file.md`
   — A.3 Functional-Layer Composition Table, used as the offline fallback
   for layer-to-group relationships when the catalog itself doesn't make a
   relationship explicit (e.g. the operator asks about a role/group
   combination not yet materialized in a concrete catalog).

## Procedure

1. **Identify the target.** Resolve the package name the operator named
   (e.g. "nvidia-driver") to its `packages` key in the catalog (e.g.
   `nvidia_driver` and/or `nvidia_driver_cuda` — a package may appear under
   more than one key; check all of them).
2. **Find every group referencing that package.** Scan `catalog.groups`
   for any group whose `components` array contains the package key.
3. **Find every functional layer referencing those groups.** Scan
   `catalog.functionallayer` for any layer whose `components` array
   contains one of the group names found in step 2.
4. **Report the direct blast radius:** every functional layer found in
   step 3, by name, with the specific group(s) that carried the package.
5. **Attempt the transitive-dependency lookup (online-preferred).** Follow
   `shared/connectivity_layer.md`'s procedure to ask a live package
   repository (one of the four approved source classes, per
   `trusted_source_policy.md`) what depends on the target package.
   - **Online reachable and well-formed:** report the resolved transitive
     dependents alongside the direct blast radius from steps 2-4.
     `disclosure=false`. Do not additionally state an offline-only
     limitation — online resolution succeeded.
   - **Online unreachable, times out, malformed, or no online access in
     this channel:** report only the functional-layer relationships found
     in steps 2-4 (declared in the catalog itself / master reference
     file). Explicitly disclose: "This analysis covers relationships
     declared in the master reference file only; transitive package
     dependencies were not evaluated because online access was
     unavailable." Follow `trusted_source_policy.md`'s audit-logging
     contract for this degraded-mode event.
6. **No group in the catalog references the package at all:** state that
   plainly — this is a valid answer (the package isn't used anywhere in
   this catalog), not an unresolved case. Do not treat "not found" as a
   degraded-mode event; only a failed *lookup attempt* (step 5's offline
   branch) is degraded-mode.
7. **Never fabricate a dependency relationship.** If steps 2-5 produce no
   evidence for a claimed relationship, do not report it as if it were
   found.

## Worked Example

> Operator: "What breaks if I remove nvidia-driver from gpu-compute?"

Given a catalog whose `slurm_node` and `login_compiler_node` functional
layers both reference `nvidia_stack_driver_groupv1`, and that group's
`components` includes `nvidia_driver` and `nvidia_driver_cuda`:

- Direct blast radius: `slurm_node_rhel_<os>_<arch>` and
  `login_compiler_node_rhel_<os>_<arch>` functional layers, via the
  `nvidia_stack_driver_groupv1` group.
- If online: also report any package that live-repository metadata shows
  as depending on `nvidia-driver` (e.g. a CUDA toolkit component with an
  explicit version requirement on the driver), with `disclosure=false`.
- If offline: report only the two functional layers above, with the
  offline-only disclosure sentence, and log the degraded-mode event per
  `trusted_source_policy.md`.

## What This Skill Does Not Do

- Cross-catalog impact tracing (out of scope, FR-3.1).
- Applying the change or updating a changelog — that is the Pre-Edit Gate
  in `ER-BSM-001-catalog-editing-skill` (not yet implemented), which calls
  this skill and then requires operator approval before any edit.
