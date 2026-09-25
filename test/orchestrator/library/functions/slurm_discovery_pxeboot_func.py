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

"""Slurm hardware-discovery verification against the desired mapping."""

import re
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from ..vars.pxeboot_vars import PXEBOOT_COMMANDS, SLURM_COMPUTE_PREFIX
from ._pxeboot_helpers import (
    group_fields,
    remote_command,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import optional_skip as _skip
from ._workload_helpers import slurm_context as _context

_HARDWARE_FIELDS = {
    "sockets": "Sockets",
    "cores_per_socket": "CoresPerSocket",
    "threads_per_core": "ThreadsPerCore",
    "real_memory": "RealMemory",
    "gres": "Gres",
}


def _parse_nodes(output: str) -> dict[str, dict[str, str]]:
    parsed = {}
    for line in output.splitlines():
        values = dict(re.findall(r"(?:^|\s)([A-Za-z][A-Za-z0-9]*)=(\S+)", line))
        if values.get("NodeName"):
            parsed[values["NodeName"]] = values
    return parsed


def _normalise(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


def _actual_hardware(node: Mapping[str, str]) -> dict[str, str]:
    return {
        input_name: str(node.get(slurm_name) or "")
        for input_name, slurm_name in _HARDWARE_FIELDS.items()
        if input_name != "gres" or str(node.get(slurm_name) or "") not in {"", "(null)"}
    }


def _expected_match(
    actual: Mapping[str, str],
    expected: Mapping[str, Any],
) -> tuple[bool, list[str]]:
    mismatches = []
    for input_name, slurm_name in _HARDWARE_FIELDS.items():
        if input_name not in expected:
            continue
        observed = actual.get(input_name, "")
        wanted = expected[input_name]
        if _normalise(observed) != _normalise(wanted):
            mismatches.append(f"{slurm_name}={observed or 'missing'} expected {wanted}")
    return not mismatches, mismatches


def check_slurm_hardware_discovery(host):
    """Verify homogeneous and heterogeneous hardware results by mapping group."""
    summary = "Slurm hardware discovery contract"
    try:
        _runtime, rows, control, config = _context(host)
        if not rows:
            return _skip(summary, "No Slurm nodes are mapped")
        compute_rows = [
            row
            for row in rows
            if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(SLURM_COMPUTE_PREFIX)
        ]
        if not compute_rows:
            return _skip(summary, "No Slurm compute nodes are mapped")

        mode = str(config.get("node_discovery_mode", "heterogeneous")).lower()
        if mode not in {"homogeneous", "heterogeneous"}:
            raise ValueError(f"Unsupported node_discovery_mode: {mode}")
        defaults = config.get("node_hardware_defaults") or {}
        if not isinstance(defaults, dict):
            raise TypeError("node_hardware_defaults must be a mapping")

        mapped_groups = {row["GROUP_NAME"] for row in compute_rows}
        unknown_groups = sorted(set(map(str, defaults)) - mapped_groups)
        result = remote_command(host, control, PXEBOOT_COMMANDS["slurm_hardware"])
        if result.rc != 0:
            raise RuntimeError("scontrol could not read discovered node hardware")
        actual_nodes = _parse_nodes(result.stdout)
        by_group: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in compute_rows:
            by_group[row["GROUP_NAME"]].append(row)

        outcomes: dict[str, tuple[bool, str]] = {}
        for group_name, group_rows in by_group.items():
            expected = defaults.get(group_name)
            group_hardware = []
            for row in group_rows:
                actual = _actual_hardware(actual_nodes.get(row["HOSTNAME"], {}))
                required = all(
                    actual.get(name)
                    for name in (
                        "sockets",
                        "cores_per_socket",
                        "threads_per_core",
                        "real_memory",
                    )
                )
                if mode == "homogeneous" and isinstance(expected, dict):
                    matches, mismatches = _expected_match(actual, expected)
                    ok = required and matches
                    detail = (
                        "user defaults applied"
                        if ok
                        else "; ".join(mismatches) or "hardware fields missing"
                    )
                else:
                    ok = required
                    detail = (
                        "runtime discovery complete"
                        if ok
                        else "hardware fields missing"
                    )
                outcomes[row["HOSTNAME"]] = (ok, detail)
                group_hardware.append(tuple(sorted(actual.items())))

            if (
                mode == "homogeneous"
                and expected is None
                and len(set(group_hardware)) > 1
            ):
                for row in group_rows:
                    outcomes[row["HOSTNAME"]] = (
                        False,
                        "nodes in the same discovery group have different hardware",
                    )

        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        groups_with = sorted(set(defaults) & mapped_groups)
        groups_without = sorted(mapped_groups - set(defaults))
        if mode == "homogeneous":
            if groups_with and groups_without:
                strategy = "mixed user defaults and representative discovery"
            elif groups_with:
                strategy = "user defaults"
            else:
                strategy = "representative discovery"
        else:
            strategy = "per-node discovery"
        return runtime_result(
            not unknown_groups and not failures,
            summary,
            [
                ("Discovery mode", mode),
                ("Effective strategy", strategy),
                ("Mapped hardware groups", ", ".join(sorted(mapped_groups))),
                ("Groups with user defaults", ", ".join(groups_with) or "none"),
                ("Groups discovered at runtime", ", ".join(groups_without) or "none"),
                ("Unknown defaults groups", ", ".join(unknown_groups) or "none"),
                *group_fields(compute_rows, outcomes),
            ],
            "; ".join(
                part
                for part in (
                    "Defaults reference unmapped groups: " + ", ".join(unknown_groups)
                    if unknown_groups
                    else "",
                    "Invalid discovered hardware: " + ", ".join(failures)
                    if failures
                    else "",
                )
                if part
            ),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
