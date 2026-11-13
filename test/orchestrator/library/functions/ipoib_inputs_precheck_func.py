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

"""ER-ORCH-005 IPoIB input validation through orchestrator.yml --tags validate.

Each case clones the active project input (credential files excluded) into a
scratch project, writes one invalid network_spec.yml or PXE mapping into the
clone, and runs the validate playbook against it. The active project input is
never modified. Errors from a baseline run of the unmodified clone are
subtracted so pre-existing, unrelated input errors cannot satisfy a case.
"""

import base64
import copy
import csv
import hashlib
import io
import ipaddress
import os
import secrets
from typing import Any

import yaml
from omnia_auto import load_test_config, run_on_host

from ..vars.cleanup_vars import CREDENTIAL_FILES
from ..vars.ipoib_vars import (
    ALL_IB_ROWS,
    CANONICAL_MAPPING_HEADERS,
    COPY_FROM,
    EVIDENCE_SUBDIR,
    EXPECT_REJECT,
    EXPLODED_FROM,
    IPOIB_COMMANDS,
    IPOIB_INPUT_CASES,
    LEGACY_IB_COLUMN,
    MAPPING_PATH_KEY,
    MAX_REPORTED_ERRORS,
    MIN_IB_ROWS,
    NETWORK_SPEC_FILE,
    DEFAULT_IB_NIC_NAME,
    ORCHESTRATOR_CONFIG_FILE,
    OUTSIDE_PREFIX,
    PROJECT_EXTRA_VAR,
    REMOTE_WRITE_CHUNK,
    SAFE_NIC_NAME,
    SCRATCH_PROJECT_PATTERN,
    SCRATCH_PROJECT_PREFIX,
    VALIDATE_TAG,
    VALIDATE_TIMEOUT_SECONDS,
    VALIDATION_RAN_MARKER,
)
from ..vars.provision_vars import DEFAULT_MAPPING_FILE
from ..vars.pxeboot_vars import SLURM_COMPUTE_PREFIX
from ._ipoib_helpers import (
    canonical_ip,
    has_ib_nic,
    ib_network_block,
    ib_subnet,
    row_address,
    validation_errors,
)
from ._prepare_helpers import read_yaml_mapping
from ._provision_helpers import _mapping_path
from ._pxeboot_helpers import runtime_exception, runtime_result
from ._workload_helpers import optional_skip
from .project_func import (
    resolve_target_input_project_path,
    resolve_target_output_project_path,
)

_BASELINE_ERRORS: dict[str, frozenset[str]] = {}

# Tracks whether this run has written the aggregated validation log yet. The
# first scratch validation of the session rewrites the active project's log
# file; later cases append to it, so one run leaves one log with every case.
_AGGREGATE_LOG_STARTED = False


class _NotApplicable(Exception):
    """The active project cannot host this case; reported as a skip."""


def _require(result, action: str) -> None:
    if result.rc != 0:
        detail = (result.stderr or result.stdout or "").strip()[:200]
        raise RuntimeError(f"{action} failed (rc={result.rc}): {detail}")


def _read_live(host) -> dict[str, Any]:
    input_dir = resolve_target_input_project_path(host)
    output_dir = resolve_target_output_project_path(host)
    mapping_path = _mapping_path(host, input_dir)
    mapping = host.file(mapping_path)
    if not mapping.is_file:
        raise ValueError(f"PXE mapping file is missing: {mapping_path}")
    return {
        "input_dir": input_dir,
        "input_root": os.path.dirname(input_dir),
        "output_root": os.path.dirname(output_dir),
        "log_root": os.path.join(os.path.dirname(os.path.dirname(input_dir)), "log"),
        "config": dict(
            read_yaml_mapping(host, os.path.join(input_dir, ORCHESTRATOR_CONFIG_FILE))
        ),
        "network_spec": dict(
            read_yaml_mapping(host, os.path.join(input_dir, NETWORK_SPEC_FILE))
        ),
        "mapping_text": mapping.content_string,
    }


def _parse_mapping(text: str) -> list[dict[str, str]]:
    """Return mapping rows normalised to the canonical 12-column contract."""
    lines = [
        line
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    records = list(csv.reader(io.StringIO("\n".join(lines))))
    if len(records) < 2:
        raise ValueError("PXE mapping has no data rows")
    header = [column.strip().upper() for column in records[0]]
    rows = []
    for record in records[1:]:
        source = dict(zip(header, (cell.strip() for cell in record)))
        row = {column: source.get(column, "") for column in CANONICAL_MAPPING_HEADERS}
        if LEGACY_IB_COLUMN in source:
            row["IB_IPV4"] = row_address(source, 4)
            row["IB_IPV6"] = row_address(source, 6)
        rows.append(row)
    return rows


def _mapping_csv(rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=CANONICAL_MAPPING_HEADERS, lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _network_yaml(network_spec: dict[str, Any]) -> str:
    return yaml.safe_dump(network_spec, sort_keys=False, explicit_start=True)


def _detect_nic_name(rows: list[dict[str, str]]) -> str:
    """Auto-detect the IB NIC name from PXE mapping rows, fallback to default."""
    for row in rows:
        name = row.get("IB_NIC_NAME", "").strip()
        if name and SAFE_NIC_NAME.fullmatch(name):
            return name
    return DEFAULT_IB_NIC_NAME


def _adjacent_network(network):
    """Return a same-size network that does not overlap the approved prefix."""
    step = network.num_addresses
    start = int(network.network_address)
    limit = (1 << network.max_prefixlen) - 1
    candidate = start + step if start + 2 * step - 1 <= limit else start - step
    return ipaddress.ip_network((candidate, network.prefixlen))


def _base_inputs(live: dict[str, Any]):
    """Return a populated clone: network_spec, rows, IB row indexes, tokens."""
    network_spec = copy.deepcopy(live["network_spec"])
    block = ib_network_block(network_spec)
    ipv4_net, ipv6_net = ib_subnet(block, 4), ib_subnet(block, 6)
    if ipv4_net is None or ipv6_net is None:
        raise _NotApplicable(
            "network_spec.yml ib_network must define IPv4 and IPv6 subnets"
        )
    rows = _parse_mapping(live["mapping_text"])
    indexes = [
        index
        for index, row in enumerate(rows)
        if row["FUNCTIONAL_GROUP_NAME"].startswith(SLURM_COMPUTE_PREFIX)
    ]
    if len(indexes) < MIN_IB_ROWS:
        raise _NotApplicable(
            f"At least {MIN_IB_ROWS} Slurm compute rows are required in the PXE mapping"
        )
    nic_name = _detect_nic_name(rows)
    used = {
        canonical_ip(row[column]) for row in rows for column in ("IB_IPV4", "IB_IPV6")
    } - {""}
    free4 = (str(addr) for addr in ipv4_net.hosts() if str(addr) not in used)
    free6 = (str(addr) for addr in ipv6_net.hosts() if str(addr) not in used)
    try:
        for index in indexes:
            row = rows[index]
            row["IB_NIC_NAME"] = row["IB_NIC_NAME"] or nic_name
            row["IB_IPV4"] = row["IB_IPV4"] or next(free4)
            row["IB_IPV6"] = row["IB_IPV6"] or next(free6)
    except StopIteration as exc:
        raise _NotApplicable("ib_network subnets have no free host addresses") from exc
    tokens = {
        "ipv6_host_1": str(ipv6_net[1]),
        "ipv6_cidr": str(ipv6_net),
        "ipv6_outside": str(_adjacent_network(ipv6_net)[1]),
    }
    return network_spec, rows, indexes, tokens


def _resolve_value(spec, ib_rows, tokens) -> str:
    if isinstance(spec, tuple):
        if spec[0] == COPY_FROM:
            return ib_rows[spec[1]][spec[2]]
        if spec[0] == EXPLODED_FROM:
            address = canonical_ip(ib_rows[spec[1]][spec[2]])
            return ipaddress.ip_address(address).exploded
        if spec[0] == OUTSIDE_PREFIX:
            return tokens["ipv6_outside"]
        raise ValueError(f"Unsupported mapping value spec: {spec[0]}")
    return str(spec).format(**tokens)


def _apply_case(case, network_spec, rows, indexes, tokens):
    """Return mutated copies, the last mutated value, and a change summary."""
    network_spec, rows = copy.deepcopy(network_spec), copy.deepcopy(rows)
    ib_rows = [rows[index] for index in indexes]
    block = ib_network_block(network_spec)
    value, changes = "", []
    for key, spec in dict(case.get("network", {})).items():
        if spec is None:
            block.pop(key, None)
            changes.append(f"network_spec ib_network.{key} removed")
            continue
        if isinstance(spec, list):
            value = [str(item).format(**tokens) for item in spec]
        else:
            value = str(spec).format(**tokens)
        block[key] = value
        changes.append(f"network_spec ib_network.{key}={value}")
    for index, column, spec in case.get("mapping", ()):
        targets = ib_rows if index == ALL_IB_ROWS else [ib_rows[index]]
        for row in targets:
            value = _resolve_value(spec, ib_rows, tokens)
            row[column] = value
        label = "all IB rows" if index == ALL_IB_ROWS else targets[0]["HOSTNAME"]
        changes.append(f"pxe_mapping {label} {column}={value or '<empty>'}")
    return network_spec, rows, str(value), changes


def _scratch_path(root: str, name: str) -> str:
    path = os.path.join(root, name)
    if not SCRATCH_PROJECT_PATTERN.fullmatch(name) or os.path.dirname(path) != root:
        raise ValueError(f"Unsafe scratch project path: {path}")
    return path


def _write_remote(host, path: str, text: str) -> None:
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    chunks = [
        encoded[start:start + REMOTE_WRITE_CHUNK]
        for start in range(0, len(encoded), REMOTE_WRITE_CHUNK)
    ] or [""]
    for position, chunk in enumerate(chunks):
        key = "write_base64_first" if position == 0 else "write_base64_append"
        _require(run_on_host(host, IPOIB_COMMANDS[key], chunk, path), f"write {path}")
    _require(run_on_host(host, IPOIB_COMMANDS["restrict_file"], path), f"restrict {path}")


def _append_remote(host, path: str, text: str, truncate: bool) -> None:
    """Write text to a remote file, truncating on the first write and appending after."""
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    chunks = [
        encoded[start:start + REMOTE_WRITE_CHUNK]
        for start in range(0, len(encoded), REMOTE_WRITE_CHUNK)
    ] or [""]
    for position, chunk in enumerate(chunks):
        key = "write_base64_first" if truncate and position == 0 else "write_base64_append"
        _require(run_on_host(host, IPOIB_COMMANDS[key], chunk, path), f"write {path}")


def _fold_scratch_log(host, live, name: str, truncate: bool) -> bool:
    """Fold a scratch validation log into the active project's single log file.

    The validator writes log/<scratch>/orchestrator_validation_<scratch>.log.
    Its contents are copied into
    log/<project>/orchestrator_validation_<project>.log, rewriting that file for
    the first case of the run and appending for later cases, so one run leaves
    one validation log under the active project with every case's output.
    Returns True when a log was written, False when the scratch log was absent.
    """
    active_project = os.path.basename(live["input_dir"])
    scratch_log_file = os.path.join(
        live["log_root"], name, f"orchestrator_validation_{name}.log"
    )
    source = host.file(scratch_log_file)
    if not source.exists:
        return False
    aggregate_dir = os.path.join(live["log_root"], active_project)
    aggregate_file = os.path.join(
        aggregate_dir, f"orchestrator_validation_{active_project}.log"
    )
    _require(
        run_on_host(host, IPOIB_COMMANDS["make_parent_dirs"], aggregate_dir),
        f"create {aggregate_dir}",
    )
    header = f"===== IPoIB input case log (scratch project {name}) =====\n"
    _append_remote(host, aggregate_file, header + source.content_string, truncate)
    return True


def _clone_project(host, live, scratch: str) -> None:
    _require(
        run_on_host(host, IPOIB_COMMANDS["path_absent"], scratch),
        "scratch project absence check",
    )
    _require(
        run_on_host(host, IPOIB_COMMANDS["make_private_dir"], scratch),
        "create scratch project",
    )
    listing = run_on_host(host, IPOIB_COMMANDS["list_input_files"], live["input_dir"])
    _require(listing, "list project input files")
    for name in filter(None, listing.stdout.splitlines()):
        if name in CREDENTIAL_FILES or "/" in name:
            continue
        _require(
            run_on_host(
                host,
                IPOIB_COMMANDS["copy_file"],
                os.path.join(live["input_dir"], name),
                os.path.join(scratch, name),
            ),
            f"copy {name}",
        )


def _run_validate(host, live, network_spec, rows):
    """Run --tags validate on a scratch clone; return (result, errors, ran).

    The scratch clone keeps the modified input away from the active project. The
    validator writes its log under log/<scratch>/; after the run that log is
    folded into the active project's single validation log
    (log/<project>/orchestrator_validation_<project>.log) — rewritten for the
    first case of the run and appended for later cases. The scratch input,
    output, and log directories are removed, so no per-case directory is left
    behind under orchestrator/log/.
    """
    from . import run_playbook  # pylint: disable=import-outside-toplevel

    global _AGGREGATE_LOG_STARTED
    name = f"{SCRATCH_PROJECT_PREFIX}{secrets.token_hex(4)}"
    scratch_input = _scratch_path(live["input_root"], name)
    scratch_output = _scratch_path(live["output_root"], name)
    scratch_log = _scratch_path(live["log_root"], name)
    try:
        _clone_project(host, live, scratch_input)
        _write_remote(
            host, os.path.join(scratch_input, NETWORK_SPEC_FILE), _network_yaml(network_spec)
        )
        _write_remote(
            host, os.path.join(scratch_input, DEFAULT_MAPPING_FILE), _mapping_csv(rows)
        )
        if str(live["config"].get(MAPPING_PATH_KEY) or "").strip():
            config = dict(live["config"], **{MAPPING_PATH_KEY: ""})
            _write_remote(
                host,
                os.path.join(scratch_input, ORCHESTRATOR_CONFIG_FILE),
                yaml.safe_dump(config, sort_keys=False, explicit_start=True),
            )
        result = run_playbook(
            tag=VALIDATE_TAG,
            extra_vars={PROJECT_EXTRA_VAR: name},
            timeout=VALIDATE_TIMEOUT_SECONDS,
        )
        if _fold_scratch_log(host, live, name, truncate=not _AGGREGATE_LOG_STARTED):
            _AGGREGATE_LOG_STARTED = True
    finally:
        for path in (scratch_input, scratch_output, scratch_log):
            run_on_host(host, IPOIB_COMMANDS["remove_scratch"], path)
    output = str(result.get("output") or "")
    return result, validation_errors(output), VALIDATION_RAN_MARKER in output


def _baseline_errors(host, live, network_spec, rows) -> frozenset[str]:
    key = hashlib.sha256(
        (_network_yaml(network_spec) + _mapping_csv(rows)).encode("utf-8")
    ).hexdigest()
    if key not in _BASELINE_ERRORS:
        _result, errors, ran = _run_validate(host, live, network_spec, rows)
        if not ran:
            raise RuntimeError(
                "Baseline validate run did not reach input validation; "
                "review the playbook output"
            )
        _BASELINE_ERRORS[key] = frozenset(errors)
    return _BASELINE_ERRORS[key]


def _save_evidence(case_key: str, network_spec, rows) -> str:
    report_path = str(load_test_config().get("report_path") or "").strip()
    if not report_path:
        raise ValueError(
            "test_config.yml report_path is required for input-validation evidence"
        )
    directory = os.path.join(report_path, EVIDENCE_SUBDIR, case_key)
    os.makedirs(directory, mode=0o750, exist_ok=True)
    with open(os.path.join(directory, NETWORK_SPEC_FILE), "w", encoding="utf-8") as handle:
        handle.write(_network_yaml(network_spec))
    with open(os.path.join(directory, DEFAULT_MAPPING_FILE), "w", encoding="utf-8") as handle:
        handle.write(_mapping_csv(rows))
    return directory


def _assess(case, value, outcome, baseline, changes, evidence):
    """Judge only errors that the baseline run did not already report."""
    result, errors, ran = outcome
    new_errors = sorted(errors - baseline)
    fields: list[tuple[str, object]] = [
        ("Expectation", case["expect"]),
        *[("Input change", change) for change in changes],
        ("Return code", result["rc"]),
        ("Baseline errors ignored", len(baseline)),
        ("New errors", len(new_errors)),
        ("Evidence", evidence),
    ]
    summary = "IPoIB input validation"
    if not ran:
        return runtime_result(
            False, summary, fields, "The validate playbook did not reach input validation"
        )
    if case["expect"] == EXPECT_REJECT:
        fragments = [str(fragment).format(value=value) for fragment in case["fragments"]]
        matched = [error for error in new_errors if all(f in error for f in fragments)]
        fields.append(("Expected fragments", " | ".join(fragments)))
        fields.extend(("Matched error", error) for error in matched[:MAX_REPORTED_ERRORS])
        fields.extend(
            ("Other new error", error)
            for error in [e for e in new_errors if e not in matched][:MAX_REPORTED_ERRORS]
        )
        success = result["rc"] != 0 and bool(matched)
        return runtime_result(
            success,
            summary,
            fields,
            "" if success else "Validation did not report the expected rejection",
        )
    fields.extend(("Unexpected error", error) for error in new_errors[:MAX_REPORTED_ERRORS])
    return runtime_result(
        not new_errors,
        summary,
        fields,
        "" if not new_errors else "Validation rejected input that the ER requires it to accept",
    )


def check_ipoib_input_case(host, case_key: str) -> dict[str, Any]:
    """Run one cataloged IPoIB input case and judge only its new errors."""
    case = IPOIB_INPUT_CASES[case_key]
    summary = f"IPoIB input case {case_key}"
    try:
        live = _read_live(host)
        live_rows = _parse_mapping(live["mapping_text"])
        if not has_ib_nic(live_rows):
            return optional_skip(summary, "No mapped node has IB_NIC_NAME")
        network_spec, rows, indexes, tokens = _base_inputs(live)
        baseline = _baseline_errors(host, live, network_spec, rows)
        case_network, case_rows, value, changes = _apply_case(
            case, network_spec, rows, indexes, tokens
        )
        evidence = _save_evidence(case_key, case_network, case_rows)
        outcome = _run_validate(host, live, case_network, case_rows)
    except _NotApplicable as exc:
        return optional_skip(summary, str(exc))
    except (OSError, RuntimeError, TypeError, ValueError, KeyError, IndexError) as exc:
        return runtime_exception(summary, exc)
    return _assess(case, value, outcome, baseline, changes, evidence)
