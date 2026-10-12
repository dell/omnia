---
name: trusted-source-policy
description: Shared trusted-source-restriction policy fragment referenced by Impact Analysis and Compatibility & Dependency Analysis. Defines the exact approved online source classes, the audit-logging contract for degraded-mode events, and the no-further-search rule when nothing can answer.
---

## Purpose

This is not a standalone operator-facing skill. It is the shared policy
fragment that `impact_analysis.md` and `compatibility_analysis.md` each
apply for FR-3 of `ER-BSM-001-analysis-skills` (trusted-source restriction)
and for the audit-logging requirement in NFR-3 (Req-SEC-I-5). Both skills
reference this file rather than duplicating its rules, so their behavior
cannot silently diverge.

## Approved Source Classes Only (HLD §4.1)

Exactly the same four classes as
`src/build_stream/ai_skills/shared/connectivity_layer.md`:

1. Red Hat Compatibility Matrix
2. Upstream documentation
3. Live package repositories
4. Local system RPM repositories — this class also covers a read-only
   read of the local Omnia source tree (e.g. to map a package to the
   playbook/role that invokes it), when the skill has file-system access.
   It is reachability under this existing class, not a fifth source
   class, since it is a local, read-only file read with no outbound
   network or FIPS/allow-list implication (Req-SEC-C-1/C-2 unaffected).

Never perform, and never cite, an open-ended general web search or an
unofficial/third-party mirror. If a request cannot be answered from these
four classes and the master reference file is also silent on it, the
answer is "unresolved" — not a broader search.

## Architecture-Mismatch Handling

If the operator's target architecture's local repo metadata isn't
available (e.g. the catalog targets `aarch64` but only `x86_64` metadata
is present locally), do not silently substitute the other architecture's
data. Stop and ask the operator to choose:

- **(a)** set up local repos for the catalog's target architecture, or
- **(b)** connect to the online approved sources instead, or
- **(c)** use the other architecture's metadata as a disclosed stand-in
  (the report must state this substitution explicitly wherever it's
  used).

Record whichever the operator chooses in the report. If the operator
declines to choose (or a proxy/stand-in is not offered), log the event
with `reason=arch-mismatch`; if the operator is offered (c) and declines
it, log `reason=operator-declined-proxy`.

## Procedure

1. **Attempt only the approved source classes** relevant to the request
   (a compatibility question favors the Compatibility Matrix and upstream
   docs; a dependency/impact question favors live package repositories).
   Follow `shared/connectivity_layer.md`'s connection procedure and
   disclosure contract for the actual attempt/fallback mechanics.
2. **Approved source answered:** report the result and cite the specific
   source consulted (e.g. "Red Hat Compatibility Matrix" or the specific
   upstream doc/repository), per FR-2's requirement. `disclosure=false`.
3. **Approved sources unreachable/malformed, master reference file has the
   data:** report from the master reference file only, with `disclosure=
   true`. State plainly which check was skipped and why (e.g. "the Red Hat
   Compatibility Matrix was not consulted").
4. **Neither approved sources nor the master reference file has the data:**
   - Do NOT broaden the search to an unapproved source to manufacture an
     answer.
   - Report the package/constraint as unresolved.
   - Flag it for manual review.
5. **Do not silently skip this policy under time pressure or an ambiguous
   request.** If in doubt whether a source qualifies as "approved," treat
   it as not approved and fall back per step 3/4.

## Audit-Logging Contract (NFR-4, Req-SEC-I-5)

Every degraded-mode event (steps 3 or 4 above) must be reconstructable
after the fact: what was requested, what the outcome was, and why it
happened.

- **When you have file-system access** (coding-agent channel): append one
  line to `src/build_stream/ai_skills/impact-analysis/degraded_mode_audit.log`
  (create the file if it does not exist) in this exact plain-text format,
  using a real shell append — no new Python code:

  ```bash
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) skill=<impact-analysis|compatibility-analysis> request=\"<operator's request, summarized>\" outcome=<degraded|unresolved> reason=<unreachable|timeout|malformed|not-in-approved-sources|not-in-master-reference|arch-mismatch|operator-declined-proxy> source_consulted=<source name or 'none'>" >> src/build_stream/ai_skills/impact-analysis/degraded_mode_audit.log
  ```

  Do not write secrets, credentials, or full request payloads into this
  file — only the summarized fields above (consistent with Req-SEC-I-6).
- **When you have no file-system access** (browser-based channel): you
  cannot append to this file. State that limitation explicitly to the
  operator as part of the disclosure — the operator-visible disclosure
  text is then the only record of the event. Do not silently skip stating
  this.
- The same disclosure fields (request, outcome, reason, source consulted)
  MUST appear in the operator-visible response regardless of channel —
  the log file is a supplementary record, not a substitute for disclosure.

## Worked Examples

**Approved source answers directly:**
> Compatibility Analysis asks the Red Hat Compatibility Matrix whether
> `nvidia-driver 550.x` is compatible with RHEL 10.2. It responds. Report
> the result, cite "Red Hat Compatibility Matrix", `disclosure=false`, no
> log entry needed (not a degraded-mode event).

**Falls back to master reference file:**
> The Compatibility Matrix times out. Fall back to A.1's OS/architecture
> constraints for `nvidia-driver`. Report `disclosure=true`, state "The Red
> Hat Compatibility Matrix was not consulted." Append (or, if no
> file-system access, disclose the inability to append) a
> `degraded_mode_audit.log` line with `outcome=degraded reason=timeout
> source_consulted=none`.

**Nothing can answer:**
> Impact Analysis is asked about a package absent from the catalog's
> functional layers, the online repository, and the master reference
> file. Report it as unresolved, flag for manual review, log
> `outcome=unresolved reason=not-in-master-reference`. Do not broaden the
> search to a general web page about the package.

**Architecture mismatch:**
> The catalog targets `aarch64`, but the execution environment only has
> `x86_64` local repo metadata subscribed and no online access. Stop and
> ask the operator to choose (a), (b), or (c). If the operator picks (c),
> disclose the `x86_64` stand-in explicitly wherever it's used in the
> report and log `outcome=degraded reason=arch-mismatch
> source_consulted=local-dnf-x86_64-stand-in`. If the operator declines
> to choose a proxy at all, log `reason=operator-declined-proxy` and
> report the affected finding as unresolved instead of guessing.
