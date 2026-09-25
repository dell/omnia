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

"""Apptainer runtime, shared-image, and download contracts after PXE."""

import re

from ..vars.pxeboot_vars import (
    APPTAINER_DOWNLOAD_MAX_RSS_KIB,
    APPTAINER_DOWNLOAD_TIMEOUT_SECONDS,
    LONG_OPERATION_POLL_SECONDS,
    PXEBOOT_COMMANDS,
)
from ._apptainer_helpers import (
    apptainer_context,
    command_error,
    grouped_node_fields,
    image_inventory,
    primary_image,
    quoted_image,
)
from ._pxeboot_helpers import (
    marker_is_authorized,
    remote_command,
    run_remote_with_progress,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import ldap_test_username, optional_skip, require_functional


def _computes_or_skip(host, summary):
    context, _rows, control, computes, _config = apptainer_context(host)
    if not computes:
        return (
            context,
            control,
            computes,
            optional_skip(summary, "No Slurm compute nodes are mapped"),
        )
    return context, control, computes, None


def _node_command_check(host, summary, command_key):
    try:
        _context, _control, computes, skipped = _computes_or_skip(host, summary)
        if skipped:
            return skipped
        outcomes = {}
        for row in computes:
            result = remote_command(host, row, PXEBOOT_COMMANDS[command_key])
            detail = (
                result.stdout.strip().splitlines()[-1]
                if result.stdout.strip()
                else command_error(result)
            )
            outcomes[row["HOSTNAME"]] = (result.rc == 0, detail)
        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failures,
            summary,
            grouped_node_fields(computes, outcomes),
            "Apptainer validation failed on: " + ", ".join(failures)
            if failures
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_runtime(host):
    """Verify the runtime and version command on every mapped compute."""
    return _node_command_check(host, "Apptainer runtime", "apptainer_runtime")


def check_apptainer_shared_artifacts(host):
    """Verify the deployed download script, image list, and shared directories."""
    return _node_command_check(
        host, "Apptainer shared artifacts", "apptainer_shared_artifacts"
    )


def check_apptainer_pulp_policy(host):
    """Verify the deployed downloader has exactly one Pulp-only pull path."""
    return _node_command_check(
        host, "Apptainer Pulp download policy", "apptainer_pulp_policy"
    )


def check_apptainer_shared_storage(host):
    """Verify /hpc_tools is a mounted shared filesystem on every compute."""
    summary = "Apptainer shared storage"
    try:
        _context, _control, computes, skipped = _computes_or_skip(host, summary)
        if skipped:
            return skipped
        outcomes = {}
        for row in computes:
            result = remote_command(
                host, row, PXEBOOT_COMMANDS["apptainer_shared_mount"]
            )
            parts = result.stdout.strip().split()
            valid = result.rc == 0 and len(parts) >= 3 and parts[-1] == "/hpc_tools"
            outcomes[row["HOSTNAME"]] = (
                valid,
                result.stdout.strip() or command_error(result),
            )
        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failures,
            summary,
            grouped_node_fields(computes, outcomes),
            "Shared /hpc_tools mount is invalid on: " + ", ".join(failures)
            if failures
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_image_inventory(host):
    """Verify every compute sees the same non-empty SIF inventory."""
    summary = "Apptainer SIF inventory"
    try:
        _context, _control, computes, skipped = _computes_or_skip(host, summary)
        if skipped:
            return skipped
        inventories = {row["HOSTNAME"]: image_inventory(host, row) for row in computes}
        reference = {
            image["name"]
            for image in inventories[computes[0]["HOSTNAME"]]
            if image["size"] > 0
        }
        if not reference and not any(inventories.values()):
            return optional_skip(
                summary,
                "No SIF image has been downloaded to /hpc_tools/container_images",
            )
        outcomes = {}
        if not any(image_inventory(host, row) for row in computes):
            return optional_skip(
                summary,
                "No SIF image has been downloaded to /hpc_tools/container_images",
            )
        for row in computes:
            names = {
                image["name"]
                for image in inventories[row["HOSTNAME"]]
                if image["size"] > 0
            }
            valid = bool(names) and names == reference
            outcomes[row["HOSTNAME"]] = (
                valid,
                f"SIF files={len(names)} | shared inventory={'matched' if names == reference else 'different'}",
            )
        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failures,
            summary,
            [
                ("Expected SIF files", len(reference)),
                *grouped_node_fields(computes, outcomes),
            ],
            "SIF inventory is empty or inconsistent on: " + ", ".join(failures)
            if failures
            else "",
        )
    except FileNotFoundError as exc:
        return optional_skip(summary, str(exc))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def _check_each_image(host, summary, probe):
    try:
        _context, _control, computes, skipped = _computes_or_skip(host, summary)
        if skipped:
            return skipped
        outcomes = {}
        for row in computes:
            images = image_inventory(host, row)
            if not images:
                outcomes[row["HOSTNAME"]] = (False, "no SIF images")
                continue
            failures = [image["name"] for image in images if not probe(row, image)]
            outcomes[row["HOSTNAME"]] = (
                not failures,
                f"verified={len(images) - len(failures)}/{len(images)}"
                + (f" | failed={','.join(failures)}" if failures else ""),
            )
        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failures,
            summary,
            grouped_node_fields(computes, outcomes),
            f"{summary} failed on: " + ", ".join(failures) if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_sif_format(host):
    """Run apptainer inspect against every discovered SIF on every compute."""
    return _check_each_image(
        host,
        "Apptainer SIF format",
        lambda row, image: (
            remote_command(
                host,
                row,
                PXEBOOT_COMMANDS["apptainer_inspect"] % quoted_image(image["path"]),
            ).rc
            == 0
        ),
    )


def check_apptainer_sif_permissions(host):
    """Verify every shared SIF is non-empty and world-readable."""
    return _check_each_image(
        host,
        "Apptainer SIF permissions",
        lambda _row, image: (
            image["size"] > 0 and image["mode"][-1:] in {"4", "5", "6", "7"}
        ),
    )


def check_apptainer_sif_integrity(host):
    """Verify the selected shared SIF has one stable checksum on every compute."""
    summary = "Apptainer SIF checksum consistency"
    try:
        _context, _control, computes, skipped = _computes_or_skip(host, summary)
        if skipped:
            return skipped
        image = primary_image(host, computes[0])
        outcomes = {}
        checksums = set()
        for row in computes:
            result = remote_command(
                host,
                row,
                PXEBOOT_COMMANDS["apptainer_checksum"] % quoted_image(image["path"]),
            )
            checksum = (
                result.stdout.split()[0]
                if result.rc == 0 and result.stdout.split()
                else ""
            )
            valid = bool(re.fullmatch(r"[a-f0-9]{64}", checksum))
            if valid:
                checksums.add(checksum)
            outcomes[row["HOSTNAME"]] = (
                valid,
                f"sha256={checksum[:12]}..." if valid else command_error(result),
            )
        consistent = len(checksums) == 1
        if not consistent:
            for name, (_ok, detail) in list(outcomes.items()):
                outcomes[name] = (False, detail + " | checksum mismatch")
        return runtime_result(
            consistent and all(outcome[0] for outcome in outcomes.values()),
            summary,
            [("Image", image["name"]), *grouped_node_fields(computes, outcomes)],
            "Shared SIF checksum differs between compute nodes"
            if not consistent
            else "",
        )
    except FileNotFoundError as exc:
        return optional_skip(summary, str(exc))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_ldap_readability(host):
    """Verify the configured LDAP test identity can read the selected SIF."""
    summary = "Apptainer LDAP SIF readability"
    try:
        context, _control, computes, skipped = _computes_or_skip(host, summary)
        if skipped:
            return skipped
        if not context["features"].get("openldap", False):
            return optional_skip(
                summary, "OpenLDAP is not selected for the mapped Slurm roles"
            )
        username = ldap_test_username()
        outcomes = {}
        for row in computes:
            image = primary_image(host, row)
            result = remote_command(
                host,
                row,
                PXEBOOT_COMMANDS["apptainer_ldap_read"]
                % (username, quoted_image(image["path"])),
            )
            outcomes[row["HOSTNAME"]] = (
                result.rc == 0,
                f"user={username} | image={image['name']} | readable={'yes' if result.rc == 0 else 'no'}",
            )
        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failures,
            summary,
            grouped_node_fields(computes, outcomes),
            "LDAP identity cannot read SIF images on: " + ", ".join(failures)
            if failures
            else "",
        )
    except FileNotFoundError as exc:
        return optional_skip(summary, str(exc))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_non_root_execution(host):
    """Execute one selected image as the configured unprivileged LDAP account."""
    summary = "Apptainer unprivileged execution"
    try:
        gated = require_functional(summary)
        if gated:
            return gated
        _context, _control, computes, skipped = _computes_or_skip(host, summary)
        if skipped:
            return skipped
        username = ldap_test_username()
        outcomes = {}
        for row in computes:
            image = primary_image(host, row)
            result = remote_command(
                host,
                row,
                PXEBOOT_COMMANDS["apptainer_non_root"]
                % (username, quoted_image(image["path"])),
            )
            uid = (
                result.stdout.strip().splitlines()[-1]
                if result.stdout.strip()
                else "missing"
            )
            outcomes[row["HOSTNAME"]] = (
                result.rc == 0 and uid.isdigit() and uid != "0",
                f"user={username} | runtime uid={uid}",
            )
        failures = [name for name, outcome in outcomes.items() if not outcome[0]]
        return runtime_result(
            not failures,
            summary,
            grouped_node_fields(computes, outcomes),
            "Unprivileged Apptainer execution failed on: " + ", ".join(failures)
            if failures
            else "",
        )
    except FileNotFoundError as exc:
        return optional_skip(summary, str(exc))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def _require_image_download(summary):
    gated = require_functional(summary)
    if gated:
        return gated
    if not marker_is_authorized("image_download"):
        return optional_skip(
            summary,
            "Select functional+image_download to authorize shared image downloads",
        )
    return None


def check_apptainer_download(host):
    """Run the deployed Pulp-only downloader and verify a usable image exists."""
    summary = "Apptainer image download"
    try:
        gated = _require_image_download(summary)
        if gated:
            return gated
        _context, _control, computes, skipped = _computes_or_skip(host, summary)
        if skipped:
            return skipped
        row = computes[0]
        result = run_remote_with_progress(
            host,
            row,
            PXEBOOT_COMMANDS["apptainer_download"] % APPTAINER_DOWNLOAD_TIMEOUT_SECONDS,
            "Apptainer image pull",
            APPTAINER_DOWNLOAD_TIMEOUT_SECONDS + LONG_OPERATION_POLL_SECONDS,
            LONG_OPERATION_POLL_SECONDS,
        )
        images = image_inventory(host, row)
        ok = result.rc == 0 and any(image["size"] > 0 for image in images)
        return runtime_result(
            ok,
            summary,
            [
                ("Execution node", f"{row['HOSTNAME']} | {row['ADMIN_IP']}"),
                ("Downloader exit code", result.rc),
                ("Usable SIF files", sum(image["size"] > 0 for image in images)),
            ],
            command_error(result) if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_download_idempotency(host):
    """Rerun the downloader and prove existing SIF files were not replaced."""
    summary = "Apptainer image download idempotency"
    try:
        gated = _require_image_download(summary)
        if gated:
            return gated
        _context, _control, computes, skipped = _computes_or_skip(host, summary)
        if skipped:
            return skipped
        row = computes[0]
        before = {
            image["name"]: (image["size"], image["modified"])
            for image in image_inventory(host, row)
        }
        if not before:
            return optional_skip(
                summary, "No existing SIF image is available for an idempotency rerun"
            )
        result = run_remote_with_progress(
            host,
            row,
            PXEBOOT_COMMANDS["apptainer_download"] % APPTAINER_DOWNLOAD_TIMEOUT_SECONDS,
            "Apptainer idempotency pull",
            APPTAINER_DOWNLOAD_TIMEOUT_SECONDS + LONG_OPERATION_POLL_SECONDS,
            LONG_OPERATION_POLL_SECONDS,
        )
        after = {
            image["name"]: (image["size"], image["modified"])
            for image in image_inventory(host, row)
        }
        unchanged = before == after
        ok = result.rc == 0 and unchanged
        return runtime_result(
            ok,
            summary,
            [
                ("Execution node", f"{row['HOSTNAME']} | {row['ADMIN_IP']}"),
                ("Existing images", len(before)),
                ("Image metadata preserved", unchanged),
            ],
            "Downloader changed an existing SIF file during an idempotency rerun"
            if not unchanged
            else (command_error(result) if result.rc != 0 else ""),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_download_memory(host):
    """Run the downloader with peak-RSS accounting and enforce a safe bound."""
    summary = "Apptainer image download memory"
    try:
        gated = _require_image_download(summary)
        if gated:
            return gated
        _context, _control, computes, skipped = _computes_or_skip(host, summary)
        if skipped:
            return skipped
        row = computes[0]
        result = run_remote_with_progress(
            host,
            row,
            PXEBOOT_COMMANDS["apptainer_download_memory"]
            % APPTAINER_DOWNLOAD_TIMEOUT_SECONDS,
            "Apptainer memory-accounted pull",
            APPTAINER_DOWNLOAD_TIMEOUT_SECONDS + LONG_OPERATION_POLL_SECONDS,
            LONG_OPERATION_POLL_SECONDS,
        )
        final_line = (
            result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
        )
        parts = final_line.split("|", 1)
        status = int(parts[0]) if len(parts) == 2 and parts[0].isdigit() else -1
        peak_kib = int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else -1
        bounded = 0 <= peak_kib <= APPTAINER_DOWNLOAD_MAX_RSS_KIB
        ok = result.rc == 0 and status == 0 and bounded
        return runtime_result(
            ok,
            summary,
            [
                ("Execution node", f"{row['HOSTNAME']} | {row['ADMIN_IP']}"),
                ("Downloader exit code", status),
                ("Peak resident memory", f"{peak_kib} KiB"),
                ("Allowed peak", f"{APPTAINER_DOWNLOAD_MAX_RSS_KIB} KiB"),
            ],
            command_error(result) if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_missing_image_contract(host):
    """Verify the downloader counts failures and exits non-zero when pulls fail."""
    return _node_command_check(
        host,
        "Apptainer missing-image failure contract",
        "apptainer_missing_image_contract",
    )
