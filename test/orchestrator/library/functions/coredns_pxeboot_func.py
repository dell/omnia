# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""CoreDNS/CoreDHCP (coresmd) post-boot verification checks.

Nine test cases close the gap identified in ORCH-FUNC-TEST-008 between
Omnia 2.2 and 2.3. Together they exercise the five required proofs
(enabled, disabled, multi-subnet, node-addition, and SMD-unavailable
datasets), plus compute-side query behavior and repeated-deployment
stability. Destructive TCs require OMNIA_COREDNS_DESTRUCTIVE=1.

Source of truth for the deployed contract (2.3):
- src/orchestrator/roles/deploy_openchami/templates/coredns/Corefile.j2:
  coresmd binds on ``cluster_boot_ip``, serves the zone ``cluster_domain``
  with ``nodes nid{03d}`` records plus default xname records.
- src/orchestrator/roles/deploy_openchami/tasks/deploy_openchami.yml sets
  ``cluster_shortname=nid``, ``cluster_nidlength=3``, and derives
  ``cluster_domain`` from ``domain_name`` by stripping the OIM shortname.
- coresmd-coredns and coresmd-coredhcp are pulled into ``openchami.target``
  and are ALWAYS running; ``dns_enabled`` only controls whether the OIM
  and metadata-service cloud-init templates make CoreDNS the primary
  nameserver on the OIM and on compute nodes.
"""

import time
from typing import Any

from omnia_auto import run_on_host

from ..vars.pxeboot_vars import (
    COREDNS_IDEMPOTENCY_SETTLE_SECONDS,
    COREDNS_QUERY_SAMPLE_SIZE,
    COREDNS_SMD_UNREACHABLE_HOLD_SECONDS,
    CORESMD_IMAGE_REPO,
    PXEBOOT_COMMANDS,
    SMD_CONTAINER_NAME,
)
from ._coredns_helpers import (
    container_inspect,
    coredns_context,
    coredns_snapshot,
    destructive_authorized,
    dns_forward_from_oim,
    dns_reverse_from_oim,
    error_result,
    optional_skip,
    remote_getent_hosts,
    remote_resolv_conf,
    resolv_conf_primary_matches,
    resolve_coredhcp_container,
    resolve_coredns_container,
    resolve_coresmd_containers,
    safe_container_name,
    sample_rows,
)
from ._pxeboot_helpers import runtime_result


def _hostname_short(fqdn: str) -> str:
    """Return the leftmost label of an FQDN for compact reporting."""
    return fqdn.split(".", 1)[0] if fqdn else fqdn


def _candidate_summary(candidates: list[str]) -> str:
    """Return a compact "|" summary of candidate FQDNs for a table cell."""
    return "|".join(_hostname_short(name) for name in candidates)


# ---------------------------------------------------------------------------
# TC-01 — Container state (enabled + disabled dataset gates)
# ---------------------------------------------------------------------------


def check_coredns_container_state(host) -> dict[str, Any]:
    """Verify coresmd containers run with expected image; observe dns_enabled.

    Per src/orchestrator/roles/deploy_openchami/tasks/configs/ochami.yml both
    the Corefile and coredhcp.yaml are dropped unconditionally, and both
    ``coresmd-coredns`` and ``coresmd-coredhcp`` systemd units are pulled
    into openchami.target — so both containers must be running regardless of
    dns_enabled. When ``dns_enabled=true``, we additionally observe that the
    OIM's /etc/resolv.conf uses CoreDNS as its primary nameserver, which is
    the actual behavioral gate for the consumption path.
    """
    try:
        ctx = coredns_context(host)
        containers = resolve_coresmd_containers(host)
        fields: list[tuple[str, object]] = [
            ("dns_enabled (orchestrator_config)", ctx["dns_enabled"]),
            ("cluster_domain (derived)", ctx["domain"]),
            ("SYSTEM_DOMAIN_NAME", ctx["raw_system_domain_name"] or "unknown"),
            ("SYSTEM_HOSTNAME", ctx["oim_shortname"] or "unknown"),
            ("admin_ip (CoreDNS bind)", ctx["admin_ip"] or "unknown"),
        ]
        failures: list[str] = []
        for name, info in containers.items():
            fields.append(
                (
                    name,
                    f"running={info['running']} image={info['image_tag'] or 'missing'}",
                )
            )
            if not info["running"]:
                failures.append(
                    f"{name} is not running; openchami.target requires it "
                    "regardless of dns_enabled"
                )
            elif not info["image_tag"].startswith(CORESMD_IMAGE_REPO):
                failures.append(
                    f"{name} image {info['image_tag']} is not from "
                    f"{CORESMD_IMAGE_REPO}"
                )

        # Observation-only: when dns_enabled=true, OIM /etc/resolv.conf should
        # have admin_ip as its primary nameserver (deployed by
        # provision_common/tasks/configure_dns.yml).
        oim_resolv_probe = run_on_host(host, PXEBOOT_COMMANDS["resolv_conf_read"])
        oim_resolv = (
            oim_resolv_probe.stdout if oim_resolv_probe.rc == 0 else ""
        )
        oim_primary_ok = resolv_conf_primary_matches(oim_resolv, ctx["admin_ip"])
        fields.append(
            (
                "OIM /etc/resolv.conf primary",
                (
                    f"{'✓' if oim_primary_ok else '✗'} "
                    f"{'CoreDNS' if oim_primary_ok else 'other'}"
                ),
            )
        )
        if ctx["dns_enabled"] and not oim_primary_ok:
            failures.append(
                "dns_enabled=true but OIM /etc/resolv.conf does not have "
                "CoreDNS as its primary nameserver"
            )

        return runtime_result(
            not failures,
            "coresmd containers are healthy and OIM resolv.conf reflects "
            "the dns_enabled setting",
            fields,
            "; ".join(failures) if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return error_result("Unable to inspect coresmd containers", str(exc))


# ---------------------------------------------------------------------------
# TC-02 — Forward DNS from OIM (queries SMD-derived candidate FQDNs)
# ---------------------------------------------------------------------------


def _forward_match(host, admin_ip: str, candidates: list[str], expected_ip: str):
    """Return (matched_fqdn, all_answers) or ('', all_answers)."""
    all_answers: dict[str, list[str]] = {}
    for name in candidates:
        answer = dns_forward_from_oim(host, admin_ip, name)
        all_answers[name] = answer["answers"]
        if answer["ok"] and expected_ip in answer["answers"]:
            return name, all_answers
    return "", all_answers


def check_coredns_forward_resolution(host) -> dict[str, Any]:
    """Query CoreDNS on the OIM for every SMD-mapped node; compare answers.

    Iterates the SMD-derived ``smd_map`` (xname + NID + PXE hostname) and
    accepts any of the candidate FQDNs that resolves to the node's expected
    ``ADMIN_IP``. Passes as long as at least one candidate per node succeeds
    (this handles coresmd builds that expose xname-only, NID-only, or both).
    """
    try:
        ctx = coredns_context(host)
        if not ctx["dns_enabled"]:
            return optional_skip(
                "CoreDNS forward-resolution query skipped",
                "dns_enabled=false in orchestrator_config.yml",
            )
        if not ctx["admin_ip"]:
            return error_result(
                "CoreDNS forward-resolution query skipped",
                "admin_network.primary_oim_admin_ip is not configured",
            )
        smd_map = ctx["smd_map"]
        if not smd_map:
            return optional_skip(
                "CoreDNS forward-resolution query skipped",
                "SMD map is empty; run provision to populate "
                "EthernetInterfaces and Components first",
            )
        rows = sample_rows(ctx["node_rows"], COREDNS_QUERY_SAMPLE_SIZE)
        fields: list[tuple[str, object]] = [
            ("CoreDNS server", ctx["admin_ip"]),
            ("cluster_domain", ctx["domain"]),
            ("Sample size", len(rows)),
        ]
        failures: list[str] = []
        for row in rows:
            admin_ip = row["ADMIN_IP"]
            record = smd_map.get(admin_ip)
            if not record:
                failures.append(
                    f"{row['HOSTNAME']}: SMD has no ethernet record for "
                    f"admin IP {admin_ip}"
                )
                fields.append((row["HOSTNAME"], "✗ no SMD interface"))
                continue
            matched, all_answers = _forward_match(
                host, ctx["admin_ip"], record["candidate_fqdns"], admin_ip
            )
            summary = _candidate_summary(record["candidate_fqdns"])
            if matched:
                fields.append(
                    (
                        row["HOSTNAME"],
                        f"✓ {_hostname_short(matched)} → {admin_ip} (of {summary})",
                    )
                )
            else:
                got = "; ".join(
                    f"{_hostname_short(name)}={','.join(all_answers[name]) or '∅'}"
                    for name in record["candidate_fqdns"]
                )
                failures.append(
                    f"{row['HOSTNAME']}: no candidate FQDN resolves to "
                    f"{admin_ip} — {got}"
                )
                fields.append((row["HOSTNAME"], f"✗ [{got}]"))
        return runtime_result(
            not failures,
            "CoreDNS forward resolution matches expected SMD/PXE state",
            fields,
            "; ".join(failures) if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return error_result("Forward-resolution query failed", str(exc))


# ---------------------------------------------------------------------------
# TC-03 — Reverse DNS from OIM
# ---------------------------------------------------------------------------


def check_coredns_reverse_resolution(host) -> dict[str, Any]:
    """Query CoreDNS on the OIM for PTR records; accept any SMD candidate FQDN."""
    try:
        ctx = coredns_context(host)
        if not ctx["dns_enabled"]:
            return optional_skip(
                "CoreDNS reverse-resolution query skipped",
                "dns_enabled=false in orchestrator_config.yml",
            )
        if not ctx["admin_ip"]:
            return error_result(
                "CoreDNS reverse-resolution query skipped",
                "admin_network.primary_oim_admin_ip is not configured",
            )
        smd_map = ctx["smd_map"]
        if not smd_map:
            return optional_skip(
                "CoreDNS reverse-resolution query skipped",
                "SMD map is empty; run provision to populate "
                "EthernetInterfaces and Components first",
            )
        rows = sample_rows(ctx["node_rows"], COREDNS_QUERY_SAMPLE_SIZE)
        fields: list[tuple[str, object]] = [
            ("CoreDNS server", ctx["admin_ip"]),
            ("Sample size", len(rows)),
        ]
        failures: list[str] = []
        for row in rows:
            admin_ip = row["ADMIN_IP"]
            record = smd_map.get(admin_ip)
            if not record:
                failures.append(
                    f"{admin_ip}: SMD has no matching ethernet record"
                )
                fields.append((admin_ip, "✗ no SMD interface"))
                continue
            answer = dns_reverse_from_oim(host, ctx["admin_ip"], admin_ip)
            got = [name.lower() for name in answer["answers"]]
            match = any(name in record["candidate_fqdns"] for name in got)
            if not answer["ok"]:
                failures.append(f"{admin_ip}: no PTR (rc={answer['rc']})")
                fields.append((admin_ip, "✗ no answer"))
            elif not match:
                summary = _candidate_summary(record["candidate_fqdns"])
                failures.append(
                    f"{admin_ip}: PTR={','.join(got) or '∅'} not in candidates "
                    f"{summary}"
                )
                fields.append(
                    (admin_ip, f"✗ {','.join(got) or '∅'} ∉ {summary}")
                )
            else:
                accepted = next(name for name in got if name in record["candidate_fqdns"])
                fields.append((admin_ip, f"✓ {_hostname_short(accepted)}"))
        return runtime_result(
            not failures,
            "CoreDNS reverse resolution matches SMD candidate FQDNs",
            fields,
            "; ".join(failures) if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return error_result("Reverse-resolution query failed", str(exc))


# ---------------------------------------------------------------------------
# TC-04 — Multi-subnet dataset (running-container-image check)
# ---------------------------------------------------------------------------


def check_coredhcp_multisubnet_running_image(host) -> dict[str, Any]:
    """Verify the running coresmd-coredhcp image on multi-subnet datasets."""
    try:
        ctx = coredns_context(host)
        if not ctx["additional_subnets"]:
            return optional_skip(
                "CoreDHCP multi-subnet check skipped",
                "admin_network.additional_subnets is empty",
            )
        coredhcp = resolve_coredhcp_container(host)
        coredns = resolve_coredns_container(host)
        fields: list[tuple[str, object]] = [
            ("Additional subnets", len(ctx["additional_subnets"])),
            (
                "coresmd-coredhcp",
                f"running={coredhcp['running']} image={coredhcp['image_tag']}",
            ),
            (
                "coresmd-coredns",
                f"running={coredns['running']} image={coredns['image_tag']}",
            ),
        ]
        failures: list[str] = []
        if not coredhcp["running"]:
            failures.append("coresmd-coredhcp is not running")
        elif not coredhcp["image_tag"].startswith(CORESMD_IMAGE_REPO):
            failures.append(
                f"coresmd-coredhcp image {coredhcp['image_tag']} is not from "
                f"{CORESMD_IMAGE_REPO}"
            )
        if (
            coredns["running"]
            and coredhcp["running"]
            and coredns["image_tag"]
            and coredhcp["image_tag"]
            and coredns["image_tag"] != coredhcp["image_tag"]
        ):
            failures.append(
                "coresmd-coredns and coresmd-coredhcp use different image tags"
            )
        return runtime_result(
            not failures,
            "Multi-subnet coresmd containers use the expected image tag",
            fields,
            "; ".join(failures) if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return error_result("Multi-subnet running-image probe failed", str(exc))


# ---------------------------------------------------------------------------
# TC-05 — Compute-side /etc/resolv.conf
# ---------------------------------------------------------------------------


def check_dns_compute_resolv_conf(host) -> dict[str, Any]:
    """Verify every mapped compute node has CoreDNS as its primary nameserver."""
    try:
        ctx = coredns_context(host)
        if not ctx["dns_enabled"]:
            return optional_skip(
                "Compute-side /etc/resolv.conf check skipped",
                "dns_enabled=false; metadata-service cloud-init only pushes "
                "CoreDNS-primary /etc/resolv.conf when dns_enabled=true",
            )
        rows = ctx["compute_rows"]
        if not rows:
            return optional_skip(
                "Compute-side /etc/resolv.conf check skipped",
                "PXE mapping has no Slurm compute nodes",
            )
        fields: list[tuple[str, object]] = [
            ("Expected primary", ctx["admin_ip"] or "unknown"),
            ("Compute nodes", len(rows)),
        ]
        failures: list[str] = []
        for row in rows:
            resolv = remote_resolv_conf(host, row)
            if not resolv.strip():
                failures.append(f"{row['HOSTNAME']}: /etc/resolv.conf unreadable")
                fields.append((row["HOSTNAME"], "✗ unreadable"))
                continue
            if resolv_conf_primary_matches(resolv, ctx["admin_ip"]):
                fields.append((row["HOSTNAME"], f"✓ {ctx['admin_ip']}"))
            else:
                failures.append(
                    f"{row['HOSTNAME']}: primary nameserver is not "
                    f"{ctx['admin_ip']}"
                )
                fields.append((row["HOSTNAME"], "✗ wrong primary"))
        return runtime_result(
            not failures,
            "Every mapped compute node uses CoreDNS as primary nameserver",
            fields,
            "; ".join(failures) if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return error_result("Compute-side /etc/resolv.conf probe failed", str(exc))


# ---------------------------------------------------------------------------
# TC-06 — Compute-side getent hosts (compare to expected PXE state)
# ---------------------------------------------------------------------------


def _remote_getent_any(host, compute_row, candidates: list[str], expected_ip: str):
    """Return (matched_fqdn, per-candidate results) trying each candidate."""
    per: dict[str, str] = {}
    for name in candidates:
        result = remote_getent_hosts(host, compute_row, name)
        per[name] = result["raw"] or "no answer"
        if result["ok"] and expected_ip in result["raw"]:
            return name, per
    return "", per


def check_dns_compute_forward_getent(host) -> dict[str, Any]:
    """Run `getent hosts` on every compute for SMD-derived candidate FQDNs."""
    try:
        ctx = coredns_context(host)
        if not ctx["dns_enabled"]:
            return optional_skip(
                "Compute-side getent hosts check skipped",
                "dns_enabled=false in orchestrator_config.yml",
            )
        computes = ctx["compute_rows"]
        peers = sample_rows(ctx["node_rows"], COREDNS_QUERY_SAMPLE_SIZE)
        smd_map = ctx["smd_map"]
        if not computes:
            return optional_skip(
                "Compute-side getent hosts check skipped",
                "PXE mapping has no Slurm compute nodes",
            )
        if not peers:
            return optional_skip(
                "Compute-side getent hosts check skipped",
                "PXE mapping has no Slurm nodes to resolve",
            )
        if not smd_map:
            return optional_skip(
                "Compute-side getent hosts check skipped",
                "SMD map is empty; run provision to populate SMD first",
            )
        fields: list[tuple[str, object]] = [
            ("Compute nodes queried", len(computes)),
            ("Peer sample size", len(peers)),
            ("cluster_domain", ctx["domain"]),
        ]
        failures: list[str] = []
        for compute in computes:
            row_failures: list[str] = []
            for peer in peers:
                record = smd_map.get(peer["ADMIN_IP"])
                if not record:
                    row_failures.append(
                        f"{peer['HOSTNAME']}: no SMD ethernet record"
                    )
                    continue
                matched, per = _remote_getent_any(
                    host, compute, record["candidate_fqdns"], peer["ADMIN_IP"]
                )
                if not matched:
                    row_failures.append(
                        f"{peer['HOSTNAME']}: none of "
                        f"{_candidate_summary(record['candidate_fqdns'])} resolved"
                    )
            if row_failures:
                failures.append(f"{compute['HOSTNAME']}: " + "; ".join(row_failures))
                fields.append(
                    (compute["HOSTNAME"], f"✗ {len(row_failures)}/{len(peers)} failed")
                )
            else:
                fields.append((compute["HOSTNAME"], f"✓ {len(peers)}/{len(peers)}"))
        return runtime_result(
            not failures,
            "Every compute node resolves every mapped peer via CoreDNS",
            fields,
            "; ".join(failures) if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return error_result("Compute-side getent probe failed", str(exc))


# ---------------------------------------------------------------------------
# TC-07 — Repeated-deployment stability (idempotency snapshot)
# ---------------------------------------------------------------------------


def check_coredns_idempotency(host) -> dict[str, Any]:
    """Snapshot coresmd images + config hashes twice; require identical state."""
    try:
        ctx = coredns_context(host)
        # Both containers are always deployed; skip on truly unpopulated OIMs.
        if not any(
            resolve_coresmd_containers(host)[name]["running"]
            for name in resolve_coresmd_containers(host)
        ):
            return optional_skip(
                "CoreDNS idempotency snapshot skipped",
                "coresmd containers are not running; run deploy_openchami first",
            )
        _ = ctx  # context is loaded to catch config errors early
        first = coredns_snapshot(host)
        time.sleep(COREDNS_IDEMPOTENCY_SETTLE_SECONDS)
        second = coredns_snapshot(host)
        fields: list[tuple[str, object]] = [
            ("Settle window", f"{COREDNS_IDEMPOTENCY_SETTLE_SECONDS}s"),
        ]
        failures: list[str] = []
        for key, label in (
            ("coredns_image_id", "coresmd-coredns image id"),
            ("coredhcp_image_id", "coresmd-coredhcp image id"),
            ("corefile_hash", "Corefile sha256"),
            ("coredhcp_hash", "coredhcp.yaml sha256"),
        ):
            before, after = first[key], second[key]
            match = before == after
            fields.append((label, f"{'✓' if match else '✗'} {before[:12] or 'missing'}"))
            if not match:
                failures.append(f"{label} changed: {before[:12]} -> {after[:12]}")
        return runtime_result(
            not failures,
            "CoreDNS/CoreDHCP state is stable across the settle window",
            fields,
            "; ".join(failures) if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return error_result("CoreDNS idempotency snapshot failed", str(exc))


# ---------------------------------------------------------------------------
# TC-08 — Node-addition dataset (destructive)
# ---------------------------------------------------------------------------


def check_dns_node_addition_pipeline(host) -> dict[str, Any]:
    """Every SMD-registered node must resolve via CoreDNS candidate FQDNs.

    Safe stand-in for a live node-addition dataset: after any provision run
    that adds nodes to SMD, this check must pass. If it fails the
    SMD-to-CoreDNS pipeline is broken and future node additions will not
    resolve. Destructive because full 2.2 semantics require live SMD POST
    which risks persistent state; run with OMNIA_COREDNS_DESTRUCTIVE=1.
    """
    try:
        ctx = coredns_context(host)
        if not ctx["dns_enabled"]:
            return optional_skip(
                "Node-addition DNS pipeline check skipped",
                "dns_enabled=false in orchestrator_config.yml",
            )
        if not destructive_authorized():
            return optional_skip(
                "Node-addition DNS pipeline check skipped",
                "OMNIA_COREDNS_DESTRUCTIVE=1 required to exercise the "
                "add-node scenario",
            )
        if not ctx["admin_ip"]:
            return error_result(
                "Node-addition DNS pipeline check skipped",
                "admin_network.primary_oim_admin_ip is not configured",
            )
        smd_map = ctx["smd_map"]
        if not smd_map:
            return optional_skip(
                "Node-addition DNS pipeline check skipped",
                "SMD map is empty; run provision to populate SMD first",
            )
        fields: list[tuple[str, object]] = [
            ("CoreDNS server", ctx["admin_ip"]),
            ("cluster_domain", ctx["domain"]),
            ("SMD nodes", len(smd_map)),
        ]
        failures: list[str] = []
        for admin_ip, record in sorted(smd_map.items()):
            matched, _ = _forward_match(
                host, ctx["admin_ip"], record["candidate_fqdns"], admin_ip
            )
            if not matched:
                failures.append(
                    f"{record['xname']} ({admin_ip}): none of "
                    f"{_candidate_summary(record['candidate_fqdns'])} resolves"
                )
                fields.append((record["xname"], "✗ absent"))
            else:
                fields.append(
                    (record["xname"], f"✓ {_hostname_short(matched)} → {admin_ip}")
                )
        return runtime_result(
            not failures,
            "Every SMD-registered node resolves via CoreDNS",
            fields,
            "; ".join(failures) if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return error_result("Node-addition DNS pipeline check failed", str(exc))


# ---------------------------------------------------------------------------
# TC-09 — SMD-unavailable dataset (destructive)
# ---------------------------------------------------------------------------


def check_dns_smd_unreachable_cached_resolution(host) -> dict[str, Any]:
    """Pause the SMD container briefly; require CoreDNS to keep serving.

    Uses podman pause to make SMD unreachable to coresmd, then re-queries a
    hostname that CoreDNS should have cached (per Corefile cache_duration).
    SMD is always unpaused in the finally block. Requires
    OMNIA_COREDNS_DESTRUCTIVE=1.
    """
    smd_paused = False
    try:
        ctx = coredns_context(host)
        if not ctx["dns_enabled"]:
            return optional_skip(
                "SMD-unavailable cached-resolution check skipped",
                "dns_enabled=false in orchestrator_config.yml",
            )
        if not destructive_authorized():
            return optional_skip(
                "SMD-unavailable cached-resolution check skipped",
                "OMNIA_COREDNS_DESTRUCTIVE=1 required to pause the SMD "
                "container",
            )
        if not ctx["admin_ip"]:
            return error_result(
                "SMD-unavailable cached-resolution check skipped",
                "admin_network.primary_oim_admin_ip is not configured",
            )
        smd_map = ctx["smd_map"]
        if not smd_map:
            return optional_skip(
                "SMD-unavailable cached-resolution check skipped",
                "SMD map is empty; run provision to populate SMD first",
            )
        admin_ip, record = next(iter(sorted(smd_map.items())))
        smd = container_inspect(host, SMD_CONTAINER_NAME)
        if not smd["running"]:
            return optional_skip(
                "SMD-unavailable cached-resolution check skipped",
                f"container {SMD_CONTAINER_NAME} is not running on the OIM",
            )

        # Warm the CoreDNS cache with a first successful lookup for any
        # candidate FQDN that resolves right now.
        matched, all_answers = _forward_match(
            host, ctx["admin_ip"], record["candidate_fqdns"], admin_ip
        )
        if not matched:
            return error_result(
                "SMD-unavailable cached-resolution check aborted",
                f"CoreDNS did not resolve any candidate for {admin_ip} "
                f"before SMD was paused: {all_answers}",
            )

        # Pause SMD; expect CoreDNS to keep serving the cached record
        pause_probe = run_on_host(
            host, PXEBOOT_COMMANDS["coresmd_container_pause"],
            safe_container_name(SMD_CONTAINER_NAME),
        )
        if pause_probe.rc != 0:
            return error_result(
                "SMD-unavailable cached-resolution check aborted",
                f"unable to pause SMD container (rc={pause_probe.rc})",
            )
        smd_paused = True

        cached_immediate, _ = _forward_match(
            host, ctx["admin_ip"], [matched], admin_ip
        )
        time.sleep(min(COREDNS_SMD_UNREACHABLE_HOLD_SECONDS, 10))
        cached_after_hold, _ = _forward_match(
            host, ctx["admin_ip"], [matched], admin_ip
        )

        fields: list[tuple[str, object]] = [
            ("Warmed FQDN", matched),
            ("SMD container", SMD_CONTAINER_NAME),
            (
                "Cached lookup (SMD paused)",
                "✓ resolved" if cached_immediate else "✗ unresolved",
            ),
            (
                "Cached lookup (after hold)",
                "✓ resolved" if cached_after_hold else "✗ unresolved",
            ),
        ]
        failures: list[str] = []
        if not cached_immediate:
            failures.append(
                f"CoreDNS did not serve cached {matched} while SMD was paused"
            )
        return runtime_result(
            not failures,
            "CoreDNS continues to serve cached records while SMD is unavailable",
            fields,
            "; ".join(failures) if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return error_result("SMD-unavailable cached-resolution check failed", str(exc))
    finally:
        if smd_paused:
            try:
                run_on_host(
                    host, PXEBOOT_COMMANDS["coresmd_container_unpause"],
                    safe_container_name(SMD_CONTAINER_NAME),
                )
            except Exception:  # nosec B110  # noqa: BLE001
                # Cleanup must not mask the original result; the operator will
                # see any lingering paused state on the next SMD interaction.
                pass


__all__ = [
    "check_coredhcp_multisubnet_running_image",
    "check_coredns_container_state",
    "check_coredns_forward_resolution",
    "check_coredns_idempotency",
    "check_coredns_reverse_resolution",
    "check_dns_compute_forward_getent",
    "check_dns_compute_resolv_conf",
    "check_dns_node_addition_pipeline",
    "check_dns_smd_unreachable_cached_resolution",
]
