---
name: compatibility-analysis
description: Cross-references a package or catalog definition against online upstream documentation and the Red Hat Compatibility Matrix, with a disclosed fallback to master reference file data only. Use when confirming whether a package/version is compatible with a target OS, architecture, or another catalog package.
---

Before starting, read `../shared/skill_scope.md` and use only this bundle's
companion skills and shared instructions.

## Purpose

Answer "is `<package>` `<version>` compatible with `<target OS/architecture
or another catalog package>`?" (`ER-BSM-001-nersc-ai-skills-catalog-
authoring`, FR-3.2, AC-009), replacing manual Compatibility Matrix research
for the operator.

## Inputs You Must Read First

1. `src/build_stream/ai_skills/shared/connectivity_layer.md` — online/
   offline fallback procedure.
2. `src/build_stream/ai_skills/impact-analysis/references/trusted_source_policy.md`
   — approved source classes and audit-logging contract.
3. `src/build_stream/ai_skills/catalog-selection-gate/references/master_reference_file.md`
   — A.1 Selection Catalogue (OS/architecture support constraints), A.6
   Pinned Version Table (the tested/reference version for the same
   component), and A.8 Constraint and Co-Requisite Table (cross-cutting
   rules such as "Kubernetes RPM, image, and repository version pins must
   agree").

## Procedure

1. **Parse the compatibility question** into: the package (and version, if
   given), and the target (an OS version/architecture, or another
   package/version).
2. **Attempt the approved online sources**, per
   `trusted_source_policy.md`: the Red Hat Compatibility Matrix for OS/
   architecture compatibility, upstream documentation for
   package-to-package or package-to-version compatibility.
   - **Reachable and well-formed:** report the compatibility result and
     cite the specific source consulted by name (e.g. "Red Hat
     Compatibility Matrix", or the specific upstream document). Flag any
     known incompatibility or unsupported combination the source states.
     `disclosure=false`.
   - **Unreachable, times out, malformed, or no online access in this
     channel:** fall back to the master reference file, restricted to the
     OS/architecture constraints and pinned-version data it actually
     records (A.1, A.6, A.8) — do not extrapolate a compatibility verdict
     the tables don't state. Explicitly disclose: "Compatibility check is
     based on master reference file data only. The Red Hat Compatibility
     Matrix was not consulted." Follow `trusted_source_policy.md`'s
     audit-logging contract for this degraded-mode event.
3. **Neither the online source nor the master reference file has an
   answer:** report the compatibility question as unresolved and flag for
   manual review (per `trusted_source_policy.md` step 4) — never guess a
   compatibility verdict.
4. **Never fabricate a compatibility result.** A "probably fine" or
   "should work" answer not backed by a cited source or a master
   reference file row is a fabrication; do not produce one.

## Worked Examples

**Online-connected:**
> Operator: "Is nvidia-driver 550.x compatible with RHEL 10.2?"
> The Red Hat Compatibility Matrix responds with a supported/unsupported
> verdict for that driver/OS pairing.
> Report the verdict, cite "Red Hat Compatibility Matrix" by name,
> `disclosure=false`.

**Degrades to master reference file:**
> Same question, Compatibility Matrix unreachable.
> A.1 records `os_version: RHEL 10.2 | supported`, content-equivalent to
> 10.0. A.6 records the pinned `nvidia_driver` version as `580.159.04` for
> the reference configuration — not `550.x`. Report: "The master reference
> file's pinned version for this configuration is 580.159.04, not 550.x;
> I cannot confirm 550.x's compatibility with RHEL 10.2 because the Red
> Hat Compatibility Matrix was not consulted." `disclosure=true`; log the
> degraded-mode event.

## What This Skill Does Not Do

- It does not replace FR-4.2's changelog compatibility-warning summary —
  that's generated as part of a diff/changelog request (the `catalog-diff`
  skill), which invokes this skill's logic but packages the result
  differently.
