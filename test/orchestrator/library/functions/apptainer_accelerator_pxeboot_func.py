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

"""Opt-in GPU and InfiniBand visibility checks inside Apptainer."""

import time

from ..vars.pxeboot_vars import APPTAINER_GPU_MEMORY_SETTLE_SECONDS, PXEBOOT_COMMANDS
from ._apptainer_helpers import (
    apptainer_context,
    command_error,
    grouped_node_fields,
    primary_image,
    quoted_image,
)
from ._pxeboot_helpers import remote_command, runtime_exception, runtime_result
from ._workload_helpers import optional_skip, require_functional, slurm_gpu_rows


def _gpu_context(host, summary):
    gated = require_functional(summary)
    if gated:
        return None, None, gated
    _context, _rows, control, computes, _config = apptainer_context(host)
    if not computes:
        return control, [], optional_skip(summary, "No Slurm compute nodes are mapped")
    gpu_rows = [entry[0] for entry in slurm_gpu_rows(host, control, computes)]
    if not gpu_rows:
        return (
            control,
            [],
            optional_skip(
                summary, "Slurm does not declare GPUs on any mapped compute node"
            ),
        )
    return control, gpu_rows, None


def _gpu_counts(host, row, image_path):
    host_result = remote_command(
        host, row, PXEBOOT_COMMANDS["apptainer_gpu_host_count"]
    )
    container_result = remote_command(
        host,
        row,
        PXEBOOT_COMMANDS["apptainer_gpu_container_count"] % quoted_image(image_path),
    )
    try:
        host_count = int(host_result.stdout.strip())
        container_count = int(container_result.stdout.strip())
    except ValueError:
        host_count = -1
        container_count = -1
    return host_result, container_result, host_count, container_count


def check_apptainer_gpu_access(host):
    """Verify every scheduler-declared GPU node exposes a GPU in Apptainer."""
    summary = "Apptainer GPU visibility"
    try:
        _control, rows, skipped = _gpu_context(host, summary)
        if skipped:
            return skipped
        outcomes = {}
        for row in rows:
            image = primary_image(host, row)
            host_result, container_result, host_count, container_count = _gpu_counts(
                host, row, image["path"]
            )
            valid = (
                host_result.rc == 0
                and container_result.rc == 0
                and host_count > 0
                and container_count > 0
            )
            outcomes[row["HOSTNAME"]] = (
                valid,
                f"host GPUs={host_count} | container GPUs={container_count}",
            )
        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failures,
            summary,
            grouped_node_fields(rows, outcomes),
            "GPU devices are not visible inside Apptainer on: " + ", ".join(failures)
            if failures
            else "",
        )
    except FileNotFoundError as exc:
        return optional_skip(summary, str(exc))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_gpu_count(host):
    """Verify container GPU count exactly matches each GPU host."""
    summary = "Apptainer GPU count"
    try:
        _control, rows, skipped = _gpu_context(host, summary)
        if skipped:
            return skipped
        outcomes = {}
        for row in rows:
            image = primary_image(host, row)
            _host_result, _container_result, host_count, container_count = _gpu_counts(
                host, row, image["path"]
            )
            outcomes[row["HOSTNAME"]] = (
                host_count > 0 and container_count == host_count,
                f"host={host_count} | container={container_count}",
            )
        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failures,
            summary,
            grouped_node_fields(rows, outcomes),
            "Container GPU counts differ on: " + ", ".join(failures)
            if failures
            else "",
        )
    except FileNotFoundError as exc:
        return optional_skip(summary, str(exc))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_cuda_workload(host):
    """Execute a bounded NVIDIA runtime command inside each GPU container."""
    summary = "Apptainer NVIDIA workload"
    try:
        _control, rows, skipped = _gpu_context(host, summary)
        if skipped:
            return skipped
        outcomes = {}
        for row in rows:
            image = primary_image(host, row)
            result = remote_command(
                host,
                row,
                PXEBOOT_COMMANDS["apptainer_gpu_workload"]
                % quoted_image(image["path"]),
            )
            gpu_lines = [
                line
                for line in result.stdout.splitlines()
                if line.strip().startswith("GPU ")
            ]
            outcomes[row["HOSTNAME"]] = (
                result.rc == 0 and bool(gpu_lines),
                f"reported devices={len(gpu_lines)}"
                + (f" | {command_error(result)}" if result.rc != 0 else ""),
            )
        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failures,
            summary,
            grouped_node_fields(rows, outcomes),
            "NVIDIA container workload failed on: " + ", ".join(failures)
            if failures
            else "",
        )
    except FileNotFoundError as exc:
        return optional_skip(summary, str(exc))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def _memory_total(output):
    values = []
    for line in output.splitlines():
        value = line.strip()
        if value.isdigit():
            values.append(int(value))
    return sum(values) if values else -1


def check_apptainer_gpu_memory(host):
    """Verify a container GPU probe does not leave material memory allocated."""
    summary = "Apptainer GPU memory release"
    try:
        _control, rows, skipped = _gpu_context(host, summary)
        if skipped:
            return skipped
        outcomes = {}
        for row in rows:
            image = primary_image(host, row)
            before = remote_command(host, row, PXEBOOT_COMMANDS["apptainer_gpu_memory"])
            workload = remote_command(
                host,
                row,
                PXEBOOT_COMMANDS["apptainer_gpu_workload"]
                % quoted_image(image["path"]),
            )
            time.sleep(APPTAINER_GPU_MEMORY_SETTLE_SECONDS)
            after = remote_command(host, row, PXEBOOT_COMMANDS["apptainer_gpu_memory"])
            before_total = _memory_total(before.stdout)
            after_total = _memory_total(after.stdout)
            released = (
                before.rc == 0
                and workload.rc == 0
                and after.rc == 0
                and before_total >= 0
                and after_total >= 0
                and after_total <= before_total + 64
            )
            outcomes[row["HOSTNAME"]] = (
                released,
                f"before={before_total} MiB | after={after_total} MiB | allowed drift=64 MiB",
            )
        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failures,
            summary,
            grouped_node_fields(rows, outcomes),
            "GPU memory did not return to its bounded baseline on: "
            + ", ".join(failures)
            if failures
            else "",
        )
    except FileNotFoundError as exc:
        return optional_skip(summary, str(exc))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_infiniband(host):
    """Verify mapped InfiniBand devices are visible inside Apptainer."""
    summary = "Apptainer InfiniBand device visibility"
    try:
        gated = require_functional(summary)
        if gated:
            return gated
        _context, _rows, _control, computes, _config = apptainer_context(host)
        ib_rows = [row for row in computes if str(row.get("IB_IP") or "").strip()]
        if not ib_rows:
            return optional_skip(summary, "No Slurm compute node has a mapped IB_IP")
        outcomes = {}
        for row in ib_rows:
            image = primary_image(host, row)
            result = remote_command(
                host,
                row,
                PXEBOOT_COMMANDS["apptainer_infiniband"] % quoted_image(image["path"]),
            )
            outcomes[row["HOSTNAME"]] = (
                result.rc == 0,
                f"IB_IP={row['IB_IP']} | /dev/infiniband={'visible' if result.rc == 0 else 'missing'}",
            )
        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failures,
            summary,
            grouped_node_fields(ib_rows, outcomes),
            "InfiniBand devices are not visible inside Apptainer on: "
            + ", ".join(failures)
            if failures
            else "",
        )
    except FileNotFoundError as exc:
        return optional_skip(summary, str(exc))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
