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

"""Private CoreDNS/CoreDHCP (coresmd) context and probe helpers.

The 2.3 orchestrator deploys the coresmd container from deploy_openchami and
renders Corefile plus coredhcp.yaml on the OIM. provision_common.configure_dns
then makes CoreDNS the primary nameserver on both the OIM and every compute
node (via /etc/resolv.conf). These helpers give the FVT suite a stable way
to observe container state, query CoreDNS from the OIM, query compute nodes,
and diff configuration hashes.
"""

import os
import re
from collections.abc import Mapping
from typing import Any

from omnia_auto import read_remote_env, run_on_host

from ..vars.pxeboot_vars import (
    COREDHCP_CONFIG_PATH,
    COREDNS_COREFILE_PATH,
    COREDNS_QUERY_TIMEOUT_SECONDS,
    CORESMD_COREDHCP_CONTAINER,
    CORESMD_COREDNS_CONTAINER,
    CORESMD_CONTAINERS,
    PXEBOOT_COMMANDS,
    SLURM_COMPUTE_PREFIX,
    SLURM_CONTROL_PREFIX,
    SLURM_LOGIN_PREFIXES,
)
from ._pxeboot_helpers import load_workload_context, remote_command, runtime_result
from ._provision_helpers import (
    api_json,
    interface_ips,
    load_context,
    normalise_mac,
    resource_list,
)

# Hardcoded coresmd zone template values from
# src/orchestrator/roles/deploy_openchami/tasks/deploy_openchami.yml:
#   cluster_shortname: "nid", cluster_nidlength: 3
# The Corefile template renders `nodes nid{03d}` which makes coresmd serve
# `nid001.{cluster_domain}` records for every node whose SMD NID is 1.
CLUSTER_SHORTNAME = "nid"
CLUSTER_NIDLENGTH = 3

_SAFE_HOSTNAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,254}")
_SAFE_IP = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}")
_SAFE_CONTAINER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")


def _derive_cluster_domain(domain_name: str, oim_shortname: str) -> str:
    """Return `cluster_domain` matching the deploy_openchami set_fact logic.

    Reproduces the Ansible regex_replace used in tasks/deploy_openchami.yml
    and tasks/refresh_openchami_configs.yml:
        cluster_domain: "{{ domain_name | regex_replace('^' + oim_node_name + '\\.', '') }}"
    So if SYSTEM_DOMAIN_NAME=oim.omnia.cluster and SYSTEM_HOSTNAME=oim,
    cluster_domain = "omnia.cluster" (what coresmd actually serves in its zone).
    """
    domain = str(domain_name or "").strip().lower()
    shortname = str(oim_shortname or "").strip().lower()
    if shortname and domain.startswith(f"{shortname}."):
        return domain[len(shortname) + 1 :]
    return domain


def coredns_context(host) -> dict[str, Any]:
    """Return dns_enabled + cluster identity + node rows + SMD hostname map.

    - `dns_enabled` controls only /etc/resolv.conf management on the OIM and
      on compute nodes via the metadata service cloud-init templates. It does
      NOT control whether coresmd-coredns and coresmd-coredhcp containers run
      (both are pulled into openchami.target and always started).
    - `cluster_domain` is derived from SYSTEM_DOMAIN_NAME with the OIM short
      hostname stripped, matching the deploy_openchami set_fact logic exactly.
    - `smd_map` joins PXE rows with SMD Ethernet interfaces and Components to
      produce, per node, the exact FQDN candidates coresmd is expected to
      serve (xname-based, NID-based, and PXE-hostname-based).
    """
    context = load_workload_context(host, load_context(host))
    orchestrator_cfg = context.get("orchestrator_config") or {}
    dns_enabled = bool(orchestrator_cfg.get("dns_enabled"))

    network_spec = context.get("network_spec") or {}
    networks = network_spec.get("Networks") or network_spec.get("networks") or []
    admin = None
    additional_subnets: list[Mapping[str, Any]] = []
    if isinstance(networks, list):
        for entry in networks:
            if isinstance(entry, dict) and isinstance(entry.get("admin_network"), dict):
                admin = entry["admin_network"]
                extra = admin.get("additional_subnets") or []
                if isinstance(extra, list):
                    additional_subnets = [
                        item for item in extra if isinstance(item, dict)
                    ]
                break
    admin_ip = str((admin or {}).get("primary_oim_admin_ip") or "").strip()
    if not admin_ip:
        env_ip = str(
            read_remote_env(host, "SYSTEM_ADMIN_NIC_IPV4", required=False) or ""
        ).strip()
        admin_ip = env_ip
    if admin_ip and not _SAFE_IP.fullmatch(admin_ip):
        raise ValueError(f"admin IP {admin_ip!r} is not a valid IPv4 address")

    raw_domain = str(context.get("domain_name") or "").strip()
    if not raw_domain:
        raw_domain = str(
            read_remote_env(host, "SYSTEM_DOMAIN_NAME", required=False) or ""
        ).strip()
    oim_shortname = str(
        read_remote_env(host, "SYSTEM_HOSTNAME", required=False) or ""
    ).strip()
    cluster_domain = _derive_cluster_domain(raw_domain, oim_shortname) or "cluster.local"

    rows = context.get("rows") or []
    slurm_prefixes = (SLURM_CONTROL_PREFIX, SLURM_COMPUTE_PREFIX, *SLURM_LOGIN_PREFIXES)
    compute_rows = [
        row
        for row in rows
        if str(row.get("EXPECTED_FUNCTIONAL_GROUP", "")).startswith(
            SLURM_COMPUTE_PREFIX
        )
    ]
    node_rows = [
        row
        for row in rows
        if str(row.get("EXPECTED_FUNCTIONAL_GROUP", "")).startswith(slurm_prefixes)
    ]

    smd_map: dict[str, dict[str, Any]] = {}
    try:
        smd_map = build_smd_dns_map(host, node_rows, cluster_domain)
    except (OSError, RuntimeError, TypeError, ValueError):
        # Provision hasn't populated SMD yet, or SMD is unreachable — leave
        # smd_map empty; individual checks report a clear skip in that case.
        smd_map = {}

    return {
        "dns_enabled": dns_enabled,
        "admin_ip": admin_ip,
        "domain": cluster_domain,
        "raw_system_domain_name": raw_domain,
        "oim_shortname": oim_shortname,
        "additional_subnets": additional_subnets,
        "compute_rows": compute_rows,
        "node_rows": node_rows,
        "smd_map": smd_map,
        "context": context,
    }


def build_smd_dns_map(
    host,
    node_rows: list[dict[str, str]],
    cluster_domain: str,
) -> dict[str, dict[str, Any]]:
    """Return `{admin_ip: {xname, nid, pxe_hostname, candidate_fqdns}}`.

    Joins the PXE mapping rows with SMD ``/hsm/v2/Inventory/EthernetInterfaces``
    (for xname lookup by admin MAC/IP) and ``/hsm/v2/State/Components`` (for
    the numeric NID). The three FQDN candidates match what coresmd v0.7 with
    the deployed Corefile actually serves:
      1. `{xname}.{cluster_domain}`  — coresmd's default xname records
      2. `{shortname}{NID:0{len}d}.{cluster_domain}` — the `nodes` template
      3. `{pxe_hostname}.{cluster_domain}` — accepted as a bonus for coresmd
         builds that surface SMD Hostname/Description as DNS records
    """
    if not node_rows:
        return {}
    interfaces = resource_list(api_json(host, "ethernet"))
    components = resource_list(api_json(host, "components"), "Components")
    nid_by_xname: dict[str, int] = {}
    for item in components:
        xname = str(item.get("ID") or "").strip()
        try:
            nid = int(item.get("NID"))
        except (TypeError, ValueError):
            continue
        if xname:
            nid_by_xname[xname] = nid

    result: dict[str, dict[str, Any]] = {}
    for row in node_rows:
        admin_ip = str(row.get("ADMIN_IP") or "").strip()
        admin_mac = normalise_mac(str(row.get("ADMIN_MAC") or ""))
        if not admin_ip:
            continue
        matches = [
            item
            for item in interfaces
            if normalise_mac(item.get("MACAddress")) == admin_mac
            and admin_ip in interface_ips(item)
        ]
        if len(matches) != 1:
            continue
        xname = str(matches[0].get("ComponentID") or "").strip()
        if not xname:
            continue
        nid = nid_by_xname.get(xname)
        candidates: list[str] = []
        if xname:
            candidates.append(f"{xname}.{cluster_domain}".lower())
        if nid is not None:
            candidates.append(
                f"{CLUSTER_SHORTNAME}{nid:0{CLUSTER_NIDLENGTH}d}.{cluster_domain}".lower()
            )
        pxe_hostname = str(row.get("HOSTNAME") or "").strip().lower()
        if pxe_hostname:
            candidates.append(f"{pxe_hostname}.{cluster_domain}".lower())
        # Deduplicate while preserving order for deterministic reporting.
        seen: set[str] = set()
        unique_candidates: list[str] = []
        for name in candidates:
            if name not in seen:
                seen.add(name)
                unique_candidates.append(name)
        result[admin_ip] = {
            "xname": xname,
            "nid": nid,
            "pxe_hostname": pxe_hostname,
            "candidate_fqdns": unique_candidates,
        }
    return result


def safe_container_name(name: str) -> str:
    """Return one shell-safe podman container name."""
    text = str(name or "").strip()
    if not _SAFE_CONTAINER.fullmatch(text):
        raise ValueError(f"container name {name!r} is invalid")
    return text


def resolve_coresmd_containers(host) -> dict[str, dict[str, Any]]:
    """Return running state and image tag for every coresmd container.

    The 2.3 orchestrator deploys two coresmd containers on the OIM:
    `coresmd-coredns` (CoreDNS) and `coresmd-coredhcp` (CoreDHCP). Both share
    the same upstream image. We inspect each one independently so tests can
    assert the coresmd DNS and DHCP planes separately.
    """
    result: dict[str, dict[str, Any]] = {}
    for name in CORESMD_CONTAINERS:
        result[name] = container_inspect(host, name)
    return result


def resolve_coredns_container(host) -> dict[str, Any]:
    """Return the coresmd-coredns container inspection result."""
    return container_inspect(host, CORESMD_COREDNS_CONTAINER)


def resolve_coredhcp_container(host) -> dict[str, Any]:
    """Return the coresmd-coredhcp container inspection result."""
    return container_inspect(host, CORESMD_COREDHCP_CONTAINER)


def container_inspect(host, container_name: str) -> dict[str, Any]:
    """Return running + effective image tag for a named podman container."""
    name = safe_container_name(container_name)
    probe = run_on_host(host, PXEBOOT_COMMANDS["coresmd_container_running"], name)
    text = probe.stdout.strip()
    if probe.rc != 0 or text == "missing":
        return {"running": False, "image_id": "", "image_tag": ""}
    parts = text.split("|", 2)
    if len(parts) != 3:
        return {"running": False, "image_id": "", "image_tag": ""}
    running = parts[0].strip().lower() == "true"
    return {
        "running": running,
        "image_id": parts[1].strip(),
        "image_tag": parts[2].strip(),
    }


def config_hash(host, path: str) -> str:
    """Return sha256 of a config file on the OIM, or 'missing'."""
    probe = run_on_host(host, PXEBOOT_COMMANDS["config_file_hash"], path)
    text = probe.stdout.strip()
    return text if text else "missing"


def coredns_snapshot(host) -> dict[str, Any]:
    """Snapshot coresmd container images and rendered CoreDNS/CoreDHCP configs."""
    coredns = resolve_coredns_container(host)
    coredhcp = resolve_coredhcp_container(host)
    return {
        "coredns_image_id": coredns["image_id"],
        "coredns_image_tag": coredns["image_tag"],
        "coredhcp_image_id": coredhcp["image_id"],
        "coredhcp_image_tag": coredhcp["image_tag"],
        "corefile_hash": config_hash(host, COREDNS_COREFILE_PATH),
        "coredhcp_hash": config_hash(host, COREDHCP_CONFIG_PATH),
    }


def safe_hostname(value: str) -> str:
    """Return one shell-safe hostname or FQDN."""
    text = str(value or "").strip()
    if not _SAFE_HOSTNAME.fullmatch(text):
        raise ValueError(f"hostname {value!r} is invalid")
    return text


def safe_ip(value: str) -> str:
    """Return one shell-safe IPv4 address."""
    text = str(value or "").strip()
    if not _SAFE_IP.fullmatch(text):
        raise ValueError(f"IP {value!r} is invalid")
    return text


def _parse_dig_output(text: str) -> list[str]:
    """Return non-empty answer lines from a dig +short response."""
    return [
        str(line.strip().rstrip("."))
        for line in text.splitlines()
        if line.strip() and not line.startswith(";")
    ]


def dns_forward_from_oim(host, admin_ip: str, name: str) -> dict[str, Any]:
    """Query CoreDNS on the OIM for A records of a mapped hostname/FQDN."""
    ip = safe_ip(admin_ip)
    query = safe_hostname(name)
    probe = run_on_host(
        host,
        PXEBOOT_COMMANDS["dns_query_forward"],
        str(COREDNS_QUERY_TIMEOUT_SECONDS),
        ip,
        query,
    )
    answers = _parse_dig_output(probe.stdout) if probe.rc == 0 else []
    filtered_answers = []
    for answer in answers:
        try:
            if _SAFE_IP.fullmatch(str(answer)):
                filtered_answers.append(answer)
        except (TypeError, ValueError):
            # Skip non-string or invalid values
            pass
    return {
        "ok": probe.rc == 0 and bool(filtered_answers),
        "answers": filtered_answers,
        "rc": probe.rc,
        "raw": probe.stdout.strip()[:200],
    }


def dns_reverse_from_oim(host, admin_ip: str, target_ip: str) -> dict[str, Any]:
    """Query CoreDNS on the OIM for the PTR record of a node's admin IP."""
    server = safe_ip(admin_ip)
    address = safe_ip(target_ip)
    probe = run_on_host(
        host,
        PXEBOOT_COMMANDS["dns_query_reverse"],
        str(COREDNS_QUERY_TIMEOUT_SECONDS),
        server,
        address,
    )
    answers = _parse_dig_output(probe.stdout) if probe.rc == 0 else []
    # Ensure all answers are strings
    string_answers = [str(a) for a in answers]
    return {
        "ok": probe.rc == 0 and bool(string_answers),
        "answers": string_answers,
        "rc": probe.rc,
        "raw": probe.stdout.strip()[:200],
    }


def remote_resolv_conf(host, row: Mapping[str, str]) -> str:
    """Return the /etc/resolv.conf contents from a compute node."""
    probe = remote_command(host, row, PXEBOOT_COMMANDS["resolv_conf_read"])
    return probe.stdout if probe.rc == 0 else ""


def remote_getent_hosts(host, row: Mapping[str, str], target: str) -> dict[str, Any]:
    """Return `getent hosts` output for a target from a compute node."""
    query = safe_hostname(target)
    probe = remote_command(host, row, PXEBOOT_COMMANDS["getent_hosts"] % (query,))
    return {
        "ok": probe.rc == 0 and bool(probe.stdout.strip()),
        "raw": probe.stdout.strip()[:200],
    }


def resolv_conf_primary_matches(resolv_text: str, admin_ip: str) -> bool:
    """Return True when the first `nameserver` line is the OIM admin IP."""
    if not admin_ip:
        return False
    target = safe_ip(admin_ip)
    for line in resolv_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("nameserver"):
            parts = stripped.split()
            if len(parts) >= 2:
                return parts[1] == target
    return False


def sample_rows(rows: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    """Return the first `limit` rows, deterministically sorted by HOSTNAME."""
    if limit <= 0:
        return list(rows)
    return sorted(rows, key=lambda r: str(r.get("HOSTNAME") or ""))[:limit]


def destructive_authorized() -> bool:
    """Return True when the operator explicitly enabled destructive tests."""
    return (
        os.environ.get("OMNIA_COREDNS_DESTRUCTIVE", "").lower()
        in {"1", "true", "yes", "on"}
    )


def optional_skip(summary: str, reason: str) -> dict[str, Any]:
    """Return the canonical skip result consumed by verify_pxeboot."""
    return runtime_result(True, summary, [("Reason", reason)], "", skipped=True)


def error_result(summary: str, error: str) -> dict[str, Any]:
    """Return a bounded failed result for a probe or exception."""
    return runtime_result(False, summary, [], error[:400])
