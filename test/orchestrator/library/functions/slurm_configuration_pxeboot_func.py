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

"""Slurm custom configuration and distribution verification."""

import re
from collections.abc import Mapping
from typing import Any

from ..vars.pxeboot_vars import PXEBOOT_COMMANDS
from ._pxeboot_helpers import (
    remote_command,
    remote_json,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import optional_skip as _skip
from ._workload_helpers import require_functional as _require_functional
from ._workload_helpers import slurm_context as _context
from .slurm_pxeboot_func import check_slurm_membership

_SUPPORTED_CONFIGS = {
    "acct_gather",
    "burst_buffer",
    "cgroup",
    "gres",
    "helpers",
    "job_container",
    "mpi",
    "oci",
    "slurm",
    "slurmdbd",
    "topology",
}


def _clean_line(line: str) -> str:
    content = line.split("#", 1)[0].strip()
    return re.sub(r"\s*=\s*", "=", re.sub(r"\s+", " ", content))


def _mapping_lines(source: Mapping[str, Any]) -> list[str]:
    lines = []
    for key, value in source.items():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    tokens = []
                    if key not in item:
                        tokens.append(str(key))
                    tokens.extend(f"{name}={entry}" for name, entry in item.items())
                    lines.append(" ".join(tokens))
                else:
                    lines.append(f"{key}={item}")
        elif isinstance(value, Mapping):
            tokens = [f"{key}={value.get(key)}"] if key in value else [str(key)]
            tokens.extend(
                f"{name}={entry}" for name, entry in value.items() if name != key
            )
            lines.append(" ".join(tokens))
        else:
            lines.append(f"{key}={value}")
    return [_clean_line(line) for line in lines if _clean_line(line)]


def _expected_lines(host, source: Any) -> list[str]:
    if isinstance(source, Mapping):
        return _mapping_lines(source)
    if isinstance(source, str) and source.startswith("/"):
        file_object = host.file(source)
        if not file_object.is_file:
            raise ValueError(f"Configured Slurm source file is missing: {source}")
        return [
            cleaned
            for line in file_object.content_string.splitlines()
            if (cleaned := _clean_line(line))
        ]
    raise TypeError("Slurm config source must be a mapping or absolute path")


def _line_tokens(line: str) -> set[str]:
    return {token.lower() for token in line.split() if token}


def _contains_expected(actual_lines: list[str], expected_line: str) -> bool:
    wanted = _line_tokens(expected_line)
    if not wanted:
        return True
    return any(wanted <= _line_tokens(actual) for actual in actual_lines)


def check_slurm_custom_configuration(host):
    """Verify configured custom values, NFS delivery, and effective visibility."""
    summary = "Slurm custom configuration end-to-end"
    try:
        _context_data, rows, control, config = _context(host)
        if not rows:
            return _skip(summary, "No Slurm nodes are mapped")
        sources = config.get("config_sources") or {}
        if not isinstance(sources, dict):
            raise TypeError("slurm_cluster.config_sources must be a mapping")
        unknown = sorted(set(sources) - _SUPPORTED_CONFIGS)
        if unknown:
            raise ValueError(
                "Unsupported Slurm config source(s): " + ", ".join(unknown)
            )

        fields: list[tuple[str, object]] = [
            (
                "Merge policy",
                "replace defaults" if config.get("skip_merge") else "merge defaults",
            ),
            ("Configured sources", ", ".join(sorted(sources)) or "none"),
        ]
        failures = []
        for config_name, source in sorted(sources.items()):
            expected = _expected_lines(host, source)
            deployed = remote_command(
                host,
                control,
                PXEBOOT_COMMANDS["slurm_config_content"] % config_name,
            )
            actual = [
                cleaned
                for line in deployed.stdout.splitlines()
                if (cleaned := _clean_line(line))
            ]
            missing = [
                line for line in expected if not _contains_expected(actual, line)
            ]
            ok = deployed.rc == 0 and not missing
            fields.append(
                (
                    f"{config_name}.conf",
                    f"{len(expected) - len(missing)}/{len(expected)} configured values matched",
                )
            )
            if not ok:
                failures.append(
                    f"{config_name}: {len(missing)} missing value(s)"
                    if deployed.rc == 0
                    else f"{config_name}: deployed file unavailable"
                )

        mount_payload = remote_json(
            host, control, PXEBOOT_COMMANDS["slurm_config_mount"]
        )
        mounts = (
            mount_payload.get("filesystems", [])
            if isinstance(mount_payload, dict)
            else []
        )
        mount = mounts[0] if len(mounts) == 1 else {}
        mount_type = str(mount.get("fstype") or "").lower()
        mount_source = str(mount.get("source") or "")
        mount_ok = mount_type in {"nfs", "nfs4"} and bool(mount_source)
        fields.append(
            (
                "Controller /etc/slurm",
                f"{mount_type or 'unmounted'} from {mount_source or 'unknown'}",
            )
        )
        if not mount_ok:
            failures.append("controller /etc/slurm is not NFS-backed")

        expected_cluster = str(config.get("cluster_name") or "")
        visibility_failures = []
        for row in rows:
            effective = remote_command(host, row, PXEBOOT_COMMANDS["slurm_config"])
            cluster = re.search(
                r"^ClusterName\s*=\s*(\S+)", effective.stdout, re.MULTILINE
            )
            if effective.rc != 0 or not cluster or cluster.group(1) != expected_cluster:
                visibility_failures.append(row["HOSTNAME"])
        fields.append(
            (
                "Effective configuration visibility",
                f"{len(rows) - len(visibility_failures)}/{len(rows)} nodes",
            )
        )
        if visibility_failures:
            failures.append(
                "effective configuration unavailable on "
                + ", ".join(visibility_failures)
            )

        return runtime_result(
            not failures,
            summary,
            fields,
            "; ".join(failures),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def _parse_config_hashes(output: str) -> dict[str, tuple[str, str]]:
    hashes = {}
    for line in output.splitlines():
        parts = line.strip().split("|", 2)
        if len(parts) != 3:
            continue
        name, path, digest = parts
        if name and path and re.fullmatch(r"[a-f0-9]{64}", digest):
            hashes[name] = (path, digest)
    return hashes


def _short_digest(digest: str) -> str:
    return f"{digest[:12]}..." if digest else "missing"


def check_slurm_configuration_consistency(host):
    """Compare controller configuration with every configless client cache."""
    summary = "Slurm configuration consistency"
    try:
        _runtime, rows, control, config = _context(host)
        if not rows:
            return _skip(summary, "No Slurm nodes are mapped")
        controller_result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_controller_config_files"],
        )
        controller_files = (
            _parse_config_hashes(controller_result.stdout)
            if controller_result.rc == 0
            else {}
        )
        client_rows = [row for row in rows if row["HOSTNAME"] != control["HOSTNAME"]]
        client_files = {}
        for row in client_rows:
            result = remote_command(
                host,
                row,
                PXEBOOT_COMMANDS["slurm_client_config_files"],
            )
            if result.rc != 0:
                client_files[row["HOSTNAME"]] = {}
            else:
                client_files[row["HOSTNAME"]] = _parse_config_hashes(result.stdout)
        required = {"slurm", "cgroup"}
        configured = set((config.get("config_sources") or {}).keys())
        required.update(configured)
        failures = []
        fields = [
            ("Authoritative node", f"{control['HOSTNAME']} | {control['ADMIN_IP']}"),
            ("Required configuration files", ", ".join(sorted(required))),
        ]
        for file_name in sorted(required):
            controller_path, controller_digest = controller_files.get(
                file_name,
                ("", ""),
            )
            controller_ok = bool(controller_path and controller_digest)
            fields.append(
                (
                    "Configuration file",
                    f"{file_name}.conf",
                )
            )
            fields.extend(
                [
                    (
                        f"  Controller {control['HOSTNAME']}",
                        f"{'✓' if controller_ok else '✗'} {control['ADMIN_IP']}",
                    ),
                    (
                        "    Path",
                        controller_path or f"/etc/slurm/{file_name}.conf",
                    ),
                    (
                        "    SHA256",
                        (
                            f"{'✓' if controller_digest else '✗'} "
                            f"{_short_digest(controller_digest)}"
                        ),
                    ),
                ]
            )
            if not controller_ok:
                failures.append(f"{file_name}.conf missing on {control['HOSTNAME']}")
            if file_name == "slurmdbd":
                fields.append(("  Configless clients", "not applicable"))
                continue
            grouped = {}
            for row in client_rows:
                grouped.setdefault(row["EXPECTED_FUNCTIONAL_GROUP"], []).append(row)
            for group_name, group_rows in grouped.items():
                group_valid = 0
                group_results = []
                for row in group_rows:
                    path, digest = client_files[row["HOSTNAME"]].get(
                        file_name,
                        ("", ""),
                    )
                    matches = (
                        controller_ok and bool(path) and digest == controller_digest
                    )
                    group_valid += int(matches)
                    group_results.append((row, path, digest, matches))
                    if not matches:
                        reason = "missing" if not path else "checksum mismatch"
                        failures.append(
                            f"{file_name}.conf {reason} on {row['HOSTNAME']}"
                        )
                fields.append(
                    (
                        "  Functional group",
                        f"[{group_name}] ({group_valid}/{len(group_rows)})",
                    )
                )
                for row, path, digest, matches in group_results:
                    fields.extend(
                        [
                            (
                                f"    {row['HOSTNAME']}",
                                f"{'✓' if matches else '✗'} {row['ADMIN_IP']}",
                            ),
                            (
                                "      Path",
                                path
                                or f"/var/spool/slurmd/conf-cache/{file_name}.conf",
                            ),
                            (
                                "      SHA256",
                                (f"{'✓' if digest else '✗'} {_short_digest(digest)}"),
                            ),
                            (
                                "      Controller checksum",
                                (
                                    f"{'✓' if matches else '✗'} "
                                    f"{'matches' if matches else 'does not match'}"
                                ),
                            ),
                        ]
                    )
        return runtime_result(
            not failures,
            summary,
            fields,
            "Configuration consistency failures: " + "; ".join(failures)
            if failures
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_slurm_configless_mode(host):
    """Verify configless controller access and cluster identity on every role."""
    summary = "Slurm configless access and cluster identity"
    try:
        _runtime, rows, _control, config = _context(host)
        if not rows:
            return _skip(summary, "No Slurm nodes are mapped")
        expected_cluster = str(config.get("cluster_name") or "")
        if not expected_cluster:
            raise ValueError(
                "slurm_cluster.cluster_name is missing in omnia_config.yml"
            )
        node_results = []
        for row in rows:
            query = remote_command(host, row, PXEBOOT_COMMANDS["slurm_config"])
            cluster_match = re.search(
                r"^ClusterName\s*=\s*(\S+)", query.stdout, re.MULTILINE
            )
            parameters_match = re.search(
                r"^SlurmctldParameters\s*=\s*(.*)$",
                query.stdout,
                re.MULTILINE,
            )
            actual_cluster = cluster_match.group(1) if cluster_match else ""
            parameters = parameters_match.group(1) if parameters_match else ""
            query_ok = query.rc == 0
            configless_ok = "enable_configless" in {
                value.strip() for value in parameters.split(",") if value.strip()
            }
            cluster_ok = actual_cluster == expected_cluster
            node_results.append(
                (
                    row,
                    query_ok and configless_ok and cluster_ok,
                    query_ok,
                    configless_ok,
                    cluster_ok,
                    actual_cluster,
                )
            )
        failed = [row["HOSTNAME"] for row, ok, *_details in node_results if not ok]
        fields = [("Expected cluster", expected_cluster)]
        grouped = {}
        for node_result in node_results:
            grouped.setdefault(node_result[0]["EXPECTED_FUNCTIONAL_GROUP"], []).append(
                node_result
            )
        for group_name, group_nodes in grouped.items():
            valid = sum(1 for _row, ok, *_details in group_nodes if ok)
            fields.append(
                ("Functional group", f"[{group_name}] ({valid}/{len(group_nodes)})")
            )
            for (
                row,
                ok,
                query_ok,
                configless_ok,
                cluster_ok,
                actual_cluster,
            ) in group_nodes:
                fields.extend(
                    [
                        (
                            f"  {row['HOSTNAME']}",
                            f"{'✓' if ok else '✗'} {row['ADMIN_IP']}",
                        ),
                        (
                            "    Controller query",
                            (
                                f"{'✓' if query_ok else '✗'} "
                                f"{'passed' if query_ok else 'failed'}"
                            ),
                        ),
                        (
                            "    Configless mode",
                            (
                                f"{'✓' if configless_ok else '✗'} "
                                f"{'enabled' if configless_ok else 'missing'}"
                            ),
                        ),
                        (
                            "    Cluster identity",
                            (
                                f"{'✓' if cluster_ok else '✗'} "
                                f"{actual_cluster or 'missing'}"
                            ),
                        ),
                    ]
                )
        return runtime_result(
            not failed,
            summary,
            fields,
            "Configless access or cluster identity failed on: " + ", ".join(failed)
            if failed
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_slurm_reconfigure(host):
    """Request a controller reconfigure and confirm all nodes remain healthy."""
    summary = "Slurm configuration reconfigure"
    try:
        gated = _require_functional(summary)
        if gated:
            return gated
        _runtime, rows, control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Slurm nodes are mapped")
        result = remote_command(host, control, PXEBOOT_COMMANDS["slurm_reconfigure"])
        membership = check_slurm_membership(host)
        ok = result.rc == 0 and membership["success"]
        return runtime_result(
            ok,
            summary,
            [
                ("scontrol reconfigure", "passed" if result.rc == 0 else "failed"),
                (
                    "Post-reconfigure nodes",
                    "healthy" if membership["success"] else "invalid",
                ),
            ],
            "Reconfigure failed or left unhealthy Slurm nodes" if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
