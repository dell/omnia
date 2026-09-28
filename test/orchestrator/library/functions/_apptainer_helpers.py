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

"""Private Apptainer context, input-validation, and execution helpers."""

import os
import re
import shlex
from collections.abc import Mapping
from typing import Any

from ..vars.pxeboot_vars import (
    APPTAINER_IMAGE_DIRECTORY,
    APPTAINER_JOB_TIMEOUT_SECONDS,
    PXEBOOT_COMMANDS,
)
from ._pxeboot_helpers import remote_command
from ._workload_helpers import slurm_compute_rows, slurm_context

_SAFE_IMAGE = re.compile(
    rf"{re.escape(APPTAINER_IMAGE_DIRECTORY)}/[A-Za-z0-9_.+-]+\.sif"
)
_SAFE_NODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,254}")
_SAFE_USERNAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,63}")


def apptainer_context(host):
    """Return workload context, Slurm rows, controller, and compute rows."""
    context, rows, control, config = slurm_context(host)
    return context, rows, control, slurm_compute_rows(rows), config


def safe_node_name(value: str) -> str:
    """Return one shell-safe mapped Slurm node name."""
    name = str(value or "").strip()
    if not _SAFE_NODE.fullmatch(name):
        raise ValueError("Mapped Slurm node name is invalid")
    return name


def safe_username(value: str) -> str:
    """Return one shell-safe POSIX account name."""
    username = str(value or "").strip()
    if not _SAFE_USERNAME.fullmatch(username):
        raise ValueError("Test account name is invalid")
    return username


def image_inventory(host, row) -> list[dict[str, Any]]:
    """Return validated SIF metadata from one mapped node."""
    result = remote_command(host, row, PXEBOOT_COMMANDS["apptainer_find_sif"])
    if result.rc != 0:
        raise RuntimeError(command_error(result))
    images = []
    for line in result.stdout.splitlines():
        parts = line.strip().split("|", 3)
        if len(parts) != 4 or not _SAFE_IMAGE.fullmatch(parts[0]):
            continue
        try:
            size = int(parts[2])
            modified = float(parts[3])
        except ValueError as exc:
            raise ValueError("SIF inventory contains invalid metadata") from exc
        images.append(
            {
                "path": parts[0],
                "name": os.path.basename(parts[0]),
                "mode": parts[1],
                "size": size,
                "modified": modified,
            }
        )
    return images


def primary_image(host, row) -> dict[str, Any]:
    """Return the first deterministic, non-empty SIF image."""
    images = [image for image in image_inventory(host, row) if image["size"] > 0]
    if not images:
        raise FileNotFoundError(
            f"No usable SIF image exists in {APPTAINER_IMAGE_DIRECTORY}"
        )
    return images[0]


def quoted_image(path: str) -> str:
    """Validate and quote an existing SIF path for a fixed command template."""
    if not _SAFE_IMAGE.fullmatch(str(path)):
        raise ValueError("SIF image path is outside the supported directory")
    return shlex.quote(path)


def command_error(result) -> str:
    """Return a bounded command failure suitable for reports."""
    detail = (result.stderr or result.stdout or f"command rc={result.rc}").strip()
    return re.sub(r"\s+", " ", detail)[:300]


def run_targeted_container(host, control, compute, image_path: str, username=""):
    """Run one synchronous Apptainer job on an exact mapped compute node."""
    node = safe_node_name(compute["HOSTNAME"])
    image = quoted_image(image_path)
    if username:
        command = PXEBOOT_COMMANDS["apptainer_srun_non_root"] % (
            APPTAINER_JOB_TIMEOUT_SECONDS,
            safe_username(username),
            node,
            image,
        )
    else:
        command = PXEBOOT_COMMANDS["apptainer_srun"] % (
            APPTAINER_JOB_TIMEOUT_SECONDS,
            node,
            image,
        )
    result = remote_command(host, control, command)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    job_line = next((line for line in lines if line.startswith("OMNIA_JOB_ID=")), "")
    job_id = job_line.partition("=")[2]
    output = [line for line in lines if line != job_line]
    hostname = output[-1].split(".", 1)[0] if output else ""
    success = result.rc == 0 and hostname == compute["HOSTNAME"]
    return {
        "success": success,
        "job_id": job_id or "not reported",
        "output": "\n".join(output) or "none",
        "error": "" if success else command_error(result),
    }


def grouped_node_fields(rows, outcomes: Mapping[str, tuple[bool, str]]):
    """Render Apptainer outcomes using the standard functional-group layout."""
    fields = []
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(row["EXPECTED_FUNCTIONAL_GROUP"], []).append(row)
    for group_name, group_rows in sorted(groups.items()):
        passed = sum(outcomes[row["HOSTNAME"]][0] for row in group_rows)
        fields.append(
            ("Functional group", f"[{group_name}] ({passed}/{len(group_rows)})")
        )
        for row in group_rows:
            ok, detail = outcomes[row["HOSTNAME"]]
            fields.append(
                (
                    f"  {row['HOSTNAME']}",
                    f"{'✓' if ok else '✗'} {row['ADMIN_IP']} | {detail}",
                )
            )
    return fields
