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

"""Opt-in Apptainer execution and Slurm integration verification."""

import os
import re
import shlex

from ..vars.pxeboot_vars import (
    APPTAINER_ARRAY_SIZE,
    APPTAINER_CONCURRENT_JOB_COUNT,
    APPTAINER_IMAGE_DIRECTORY,
    APPTAINER_JOB_TIMEOUT_SECONDS,
    PXEBOOT_COMMANDS,
)
from ._apptainer_helpers import (
    apptainer_context,
    command_error,
    grouped_node_fields,
    primary_image,
    quoted_image,
    run_targeted_container,
    safe_node_name,
)
from ._pxeboot_helpers import remote_command, runtime_exception, runtime_result
from ._workload_helpers import ldap_test_username, optional_skip, require_functional


def _functional_context(host, summary):
    gated = require_functional(summary)
    if gated:
        return None, None, None, None, gated
    context, rows, control, computes, _config = apptainer_context(host)
    if not computes:
        return (
            context,
            rows,
            control,
            computes,
            optional_skip(summary, "No Slurm compute nodes are mapped"),
        )
    try:
        image = primary_image(host, computes[0])
    except FileNotFoundError as exc:
        return context, rows, control, computes, optional_skip(summary, str(exc))
    return context, rows, control, computes, image


def _targeted_job_check(host, summary, username=""):
    try:
        _context, _rows, control, computes, image_or_result = _functional_context(
            host, summary
        )
        if isinstance(image_or_result, dict) and "skipped" in image_or_result:
            return image_or_result
        image = image_or_result
        outcomes = {}
        for row in computes:
            result = run_targeted_container(
                host, control, row, image["path"], username=username
            )
            outcomes[row["HOSTNAME"]] = (
                result["success"],
                f"job={result['job_id']} | output={result['output']}"
                + (f" | error={result['error']}" if result["error"] else ""),
            )
        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        fields = [("Image", image["name"])]
        if username:
            fields.append(("Submission identity", username))
        fields.extend(grouped_node_fields(computes, outcomes))
        return runtime_result(
            not failures,
            summary,
            fields,
            "Targeted Apptainer jobs failed on: " + ", ".join(failures)
            if failures
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_single_node_job(host):
    """Run one synchronous Apptainer job on every mapped compute node."""
    return _targeted_job_check(host, "Apptainer targeted single-node jobs")


def check_apptainer_multi_node_job(host):
    """Run one Apptainer allocation spanning multiple compute nodes."""
    summary = "Apptainer multi-node Slurm job"
    try:
        _context, _rows, control, computes, image_or_result = _functional_context(
            host, summary
        )
        if isinstance(image_or_result, dict) and "skipped" in image_or_result:
            return image_or_result
        if len(computes) < 2:
            return optional_skip(
                summary, "At least two Slurm compute nodes are required"
            )
        image = image_or_result
        count = len(computes)
        result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["apptainer_multi_srun"]
            % (
                APPTAINER_JOB_TIMEOUT_SECONDS,
                count,
                count,
                quoted_image(image["path"]),
            ),
        )
        reported = {
            line.strip().split(".", 1)[0]
            for line in result.stdout.splitlines()
            if line.strip()
        }
        mapped = {row["HOSTNAME"] for row in computes}
        ok = result.rc == 0 and reported == mapped
        return runtime_result(
            ok,
            summary,
            [
                ("Image", image["name"]),
                ("Requested nodes", count),
                ("Mapped nodes", ", ".join(sorted(mapped))),
                ("Container output nodes", ", ".join(sorted(reported)) or "none"),
            ],
            "Multi-node container output did not match mapped compute nodes"
            if not ok
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_ldap_job(host):
    """Run one targeted Apptainer job per compute as the LDAP test identity."""
    summary = "Apptainer LDAP-user Slurm jobs"
    try:
        context, _rows, _control, _computes, _result = _functional_context(
            host, summary
        )
        if isinstance(_result, dict) and "skipped" in _result:
            return _result
        if not context["features"].get("openldap", False):
            return optional_skip(
                summary, "OpenLDAP is not selected for the mapped Slurm roles"
            )
        return _targeted_job_check(host, summary, username=ldap_test_username())
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_concurrent_jobs(host):
    """Run concurrent targeted Apptainer jobs and verify every output."""
    summary = "Apptainer concurrent Slurm jobs"
    try:
        _context, _rows, control, computes, image_or_result = _functional_context(
            host, summary
        )
        if isinstance(image_or_result, dict) and "skipped" in image_or_result:
            return image_or_result
        image = image_or_result
        targets = computes[: min(len(computes), APPTAINER_CONCURRENT_JOB_COUNT)]
        fragments = []
        output_paths = []
        for index, row in enumerate(targets):
            node = safe_node_name(row["HOSTNAME"])
            output_variable = f"omnia_output_{index}"
            output_paths.append((node, output_variable))
            fragments.append(
                f"{output_variable}=$(mktemp --tmpdir "
                f'"omnia-apptainer-{node}.XXXXXX") || exit 1;'
            )
            fragments.append(
                "srun --nodes=1 --ntasks=1 --nodelist="
                f"{node} apptainer exec {quoted_image(image['path'])} hostname -s "
                f'>"${{{output_variable}}}" 2>&1 &'
            )
        fragments.append("wait;")
        for _node, output_variable in output_paths:
            fragments.append(f'cat "${{{output_variable}}}";')
            fragments.append(f'rm -f -- "${{{output_variable}}}";')
        script = " ".join(fragments)
        result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["apptainer_concurrent_srun"]
            % (APPTAINER_JOB_TIMEOUT_SECONDS, shlex.quote(script)),
        )
        reported = [
            line.strip().split(".", 1)[0]
            for line in result.stdout.splitlines()
            if line.strip()
        ]
        expected = [row["HOSTNAME"] for row in targets]
        ok = result.rc == 0 and sorted(reported) == sorted(expected)
        return runtime_result(
            ok,
            summary,
            [
                ("Concurrent jobs", len(targets)),
                ("Expected nodes", ", ".join(expected)),
                ("Completed outputs", ", ".join(reported) or "none"),
            ],
            command_error(result) if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_invalid_sif(host):
    """Verify Slurm reports failure for a nonexistent SIF path."""
    summary = "Apptainer invalid-SIF rejection"
    try:
        gated = require_functional(summary)
        if gated:
            return gated
        _context, _rows, control, computes, _config = apptainer_context(host)
        if not computes:
            return optional_skip(summary, "No Slurm compute nodes are mapped")
        node = safe_node_name(computes[0]["HOSTNAME"])
        result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["apptainer_invalid_sif"]
            % (APPTAINER_JOB_TIMEOUT_SECONDS, node),
        )
        rejected = result.rc != 0
        return runtime_result(
            rejected,
            summary,
            [
                ("Target node", node),
                ("Nonexistent image", ".omnia-invalid.sif"),
                ("Execution rejected", rejected),
            ],
            "A nonexistent SIF unexpectedly executed successfully"
            if not rejected
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_restricted_sif(host):
    """Verify an unprivileged user cannot execute a mode-0600 SIF copy."""
    summary = "Apptainer restricted-SIF rejection"
    restricted = ""
    row = None
    try:
        _context, _rows, _control, computes, image_or_result = _functional_context(
            host, summary
        )
        if isinstance(image_or_result, dict) and "skipped" in image_or_result:
            return image_or_result
        row = computes[0]
        image = image_or_result
        run_id = re.sub(r"[^A-Za-z0-9_-]", "", os.environ.get("RUN_ID", "run"))[:40]
        restricted = f"{APPTAINER_IMAGE_DIRECTORY}/.omnia-restricted-{run_id}.sif"
        prepare = remote_command(
            host,
            row,
            PXEBOOT_COMMANDS["apptainer_restricted_prepare"]
            % (
                quoted_image(image["path"]),
                shlex.quote(restricted),
                shlex.quote(restricted),
            ),
        )
        if prepare.rc != 0:
            raise RuntimeError(command_error(prepare))
        execution = remote_command(
            host,
            row,
            PXEBOOT_COMMANDS["apptainer_restricted_exec"] % shlex.quote(restricted),
        )
        rejected = execution.rc != 0
        return runtime_result(
            rejected,
            summary,
            [
                ("Validation node", f"{row['HOSTNAME']} | {row['ADMIN_IP']}"),
                ("Restricted mode", "0600"),
                ("Unprivileged execution rejected", rejected),
            ],
            "An unprivileged account executed a mode-0600 SIF" if not rejected else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
    finally:
        if row is not None and restricted:
            try:
                remote_command(
                    host,
                    row,
                    PXEBOOT_COMMANDS["apptainer_restricted_cleanup"]
                    % shlex.quote(restricted),
                )
            except (OSError, RuntimeError, TypeError, ValueError):
                pass


def check_apptainer_nfs_visibility(host):
    """Verify every targeted container can read its SIF through /hpc_tools."""
    summary = "Apptainer shared-storage visibility"
    try:
        _context, _rows, control, computes, image_or_result = _functional_context(
            host, summary
        )
        if isinstance(image_or_result, dict) and "skipped" in image_or_result:
            return image_or_result
        image = image_or_result
        outcomes = {}
        for row in computes:
            result = remote_command(
                host,
                control,
                PXEBOOT_COMMANDS["apptainer_srun_nfs"]
                % (
                    APPTAINER_JOB_TIMEOUT_SECONDS,
                    safe_node_name(row["HOSTNAME"]),
                    quoted_image(image["path"]),
                    shlex.quote(image["name"]),
                ),
            )
            outcomes[row["HOSTNAME"]] = (
                result.rc == 0,
                f"container read /hpc_tools/container_images/{image['name']}",
            )
        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failures,
            summary,
            grouped_node_fields(computes, outcomes),
            "Shared image was not visible inside containers on: " + ", ".join(failures)
            if failures
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_slurm_environment(host):
    """Verify Slurm allocation variables are preserved inside Apptainer."""
    summary = "Apptainer Slurm environment propagation"
    try:
        _context, _rows, control, computes, image_or_result = _functional_context(
            host, summary
        )
        if isinstance(image_or_result, dict) and "skipped" in image_or_result:
            return image_or_result
        image = image_or_result
        outcomes = {}
        for row in computes:
            result = remote_command(
                host,
                control,
                PXEBOOT_COMMANDS["apptainer_srun_environment"]
                % (
                    APPTAINER_JOB_TIMEOUT_SECONDS,
                    safe_node_name(row["HOSTNAME"]),
                    quoted_image(image["path"]),
                ),
            )
            parts = result.stdout.strip().split("|", 1)
            valid = (
                result.rc == 0
                and len(parts) == 2
                and parts[0].isdigit()
                and parts[1].isdigit()
            )
            outcomes[row["HOSTNAME"]] = (
                valid,
                f"SLURM_JOB_ID={parts[0] if parts else 'missing'} | SLURM_NODEID={parts[1] if len(parts) > 1 else 'missing'}",
            )
        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failures,
            summary,
            grouped_node_fields(computes, outcomes),
            "Slurm allocation variables were missing inside containers on: "
            + ", ".join(failures)
            if failures
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_job_array(host):
    """Submit an Apptainer Slurm array and wait for every task to complete."""
    summary = "Apptainer Slurm job array"
    try:
        _context, _rows, control, _computes, image_or_result = _functional_context(
            host, summary
        )
        if isinstance(image_or_result, dict) and "skipped" in image_or_result:
            return image_or_result
        image = image_or_result
        wrap = shlex.quote(f"apptainer exec {image['path']} hostname -s")
        result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["apptainer_array_submit"]
            % (APPTAINER_JOB_TIMEOUT_SECONDS, APPTAINER_ARRAY_SIZE - 1, wrap),
        )
        job_id = result.stdout.strip().split(";", 1)[0]
        valid_id = bool(re.fullmatch(r"[0-9]+", job_id))
        ok = result.rc == 0 and valid_id
        return runtime_result(
            ok,
            summary,
            [
                ("Array tasks", APPTAINER_ARRAY_SIZE),
                ("Job ID", job_id or "not reported"),
                ("All tasks completed", result.rc == 0),
            ],
            command_error(result) if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_failure_cleanup(host):
    """Verify a failed invalid-image job leaves no matching runtime process."""
    summary = "Apptainer failed-job cleanup"
    try:
        gated = require_functional(summary)
        if gated:
            return gated
        _context, _rows, control, computes, _config = apptainer_context(host)
        if not computes:
            return optional_skip(summary, "No Slurm compute nodes are mapped")
        node = safe_node_name(computes[0]["HOSTNAME"])
        failed = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["apptainer_invalid_sif"]
            % (APPTAINER_JOB_TIMEOUT_SECONDS, node),
        )
        probe = remote_command(
            host,
            computes[0],
            PXEBOOT_COMMANDS["apptainer_process_probe"]
            % shlex.quote(".omnia-invalid.sif"),
        )
        no_orphan = probe.rc != 0 and not probe.stdout.strip()
        ok = failed.rc != 0 and no_orphan
        return runtime_result(
            ok,
            summary,
            [
                ("Target node", node),
                ("Invalid-image job failed", failed.rc != 0),
                (
                    "Matching orphan processes",
                    "none" if no_orphan else probe.stdout.strip()[:200],
                ),
            ],
            "Invalid-image execution did not fail cleanly" if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
