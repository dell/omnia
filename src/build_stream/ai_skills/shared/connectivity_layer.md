---
name: online-offline-connectivity-layer
description: Shared online/offline fallback decision procedure for package-metadata, impact, and compatibility resolution. Referenced (not duplicated) by the Catalog Generation skill and, later, by the Analysis skills. Channel-agnostic.
---

## Purpose

This is not a standalone operator-facing skill. It is the shared
connectivity-decision procedure that any catalog-authoring or analysis skill
follows when it needs to resolve package metadata, a compatibility fact, or
an impact relationship that is not already fixed by the master reference
file's pinned tables (A.5, A.6). It implements FR-3 of
`ER-BSM-001-catalog-generation-skill` and is the shared foundation
`ER-BSM-001-analysis-skills` reuses for FR-3.1 (Impact Analysis) and FR-3.2
(Compatibility & Dependency Analysis).

Every skill that references this file MUST follow the same disclosure
contract below — the packaging is a shared instructions file, not a
duplicated-but-possibly-diverging description per skill (per the resolved
Open Question in `ER-BSM-001-catalog-generation-skill`'s `spec.md`, §8).

## Approved Source Classes Only

Prefer, in this order, only the following source classes (HLD §4.1 of
`ER-BSM-001-nersc-ai-skills-catalog-authoring`):

1. **Red Hat Compatibility Matrix** — OS/architecture/package compatibility
   facts.
2. **Upstream documentation** — package-specific metadata and compatibility
   notes published by the package's own project.
3. **Live package repositories** — the repositories named in the master
   reference file's A.5 Package Source Defaults Table (e.g. querying the
   repository's own metadata for a package's available versions).
4. **Local system RPM repositories** (DNF/YUM metadata for RHEL, EPEL, etc.)
   when reachable from the execution environment.

Never perform, and never cite, an open-ended general web search or an
unofficial/third-party mirror. If none of the four source classes above can
resolve the request, treat it as "online access unavailable" for that
request and fall back per the Procedure below — do not substitute a fifth,
unapproved source.

## Procedure

1. **Attempt the approved online source(s)** for the requested package
   metadata, compatibility fact, or impact relationship, using HTTPS with
   FIPS 140-2 compliant cryptographic modules where the execution
   environment provides that guarantee (Req-SEC-C-1). Respect any
   NERSC-approved outbound allow-list already configured in the execution
   environment (Req-SEC-C-2) — do not attempt to bypass it.
2. **Online source responded successfully and the response is well-formed:**
   - Return the online-sourced data.
   - Set `disclosure=false`.
   - Do not additionally consult the master reference file for the same
     request.
3. **Online source is unreachable, times out, or returns malformed data:**
   - Fall back to the master reference file
     (`master_reference/master_reference_file.md`) for the same request.
   - Set `disclosure=true`.
   - State plainly to the operator which condition triggered the fallback
     (unreachable / timeout / malformed response) and that the data
     returned is master-reference-file-only.
4. **Master reference file also lacks the requested data (both paths
   exhausted):**
   - Do NOT fabricate the missing data.
   - Report that the data is not available online or in the offline
     reference file.
   - Flag the request for manual review or a later online-resolution
     attempt.
5. **No online attempt is possible in this channel** (e.g. a browser-based
   AI assistant with no outbound network access of its own): skip step 1,
   go directly to step 3's fallback behavior, and disclose that no online
   attempt was made because the channel cannot perform one — do not claim
   an online source was consulted when it wasn't.

## Disclosure Contract (must not diverge across skills)

Every skill invoking this procedure returns (or states, in a browser-based
channel) the same two-part result:

| Field | Meaning |
|-------|---------|
| `data` | The resolved value, from whichever source resolved it |
| `disclosure` | `false` when sourced online and well-formed; `true` whenever the master reference file was used instead |

Consuming skills MUST surface `disclosure=true` to the operator in plain
language (e.g. "This result is based on the master reference file only;
the Red Hat Compatibility Matrix was not consulted.") rather than only
recording it internally.

## Worked Examples

**Online reachable:**
> A skill needs the latest compatible NVIDIA driver version for RHEL 10.2.
> The CUDA repository responds with a valid version list.
> Result: `disclosure=false`; return the version from the repository
> response.

**Online unreachable, offline fallback used:**
> The same request, but the CUDA repository times out.
> Result: fall back to A.6 Pinned Version Table's `nvidia_driver` row;
> `disclosure=true`; state: "The CUDA repository timed out, so this
> result is based on the master reference file's pinned version only."

**Both exhausted:**
> A skill needs compatibility data for a package absent from every online
> source consulted and from every A.5/A.6 row.
> Result: report the gap; do not fabricate a version or compatibility
> verdict; flag for manual review.
