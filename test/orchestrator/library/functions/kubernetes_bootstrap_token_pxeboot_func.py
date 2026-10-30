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

"""Bootstrap token security and TTL verification after Kubernetes provisioning."""

import re
from datetime import datetime, timezone

from ..vars.pxeboot_vars import PXEBOOT_COMMANDS
from ._pxeboot_helpers import (
    remote_command,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import kubernetes_context as _context
from ._workload_helpers import optional_skip as _skip
from .kubernetes_storage_pxeboot_func import _kubernetes_nfs_storage

# Regex applied by ms-group-service_kube_node_x86_64.yaml.j2
_WORKER_JOIN_RE = re.compile(
    r"^kubeadm join (?:[0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]{1,5}"
    r" --token [a-z0-9]{6}\.[a-z0-9]{16}"
    r" --discovery-token-ca-cert-hash sha256:[a-f0-9]{64}$"
)

# Regex applied by ms-group-service_kube_control_plane_x86_64.yaml.j2
_CP_JOIN_RE = re.compile(
    r"^kubeadm join (?:[0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]{1,5}"
    r" --token [a-z0-9]{6}\.[a-z0-9]{16}"
    r" --discovery-token-ca-cert-hash sha256:[a-f0-9]{64}"
    r" --control-plane --certificate-key [a-f0-9]{64}$"
)

_WORKER_JOIN_FILE = "worker-join-command.sh"
_CP_JOIN_FILE = "control-plane-join-command.sh"
_REFRESH_SCRIPT = "generate-control-plane-join.sh"

# Tolerance added to configured TTL when checking EXPIRES timestamp
_TTL_TOLERANCE_SECONDS = 120


def _resolve_mount_point(host):
    """Return (context, control_row, mount_point) for the deployed k8s cluster."""
    context, rows, control, config = _context(host)
    if not rows:
        return context, None, None, None
    storage = _kubernetes_nfs_storage(context, config)
    return context, control, storage["mount_point"], config


def _join_file_path(mount_point, filename):
    return f"{mount_point}/{filename}"


def _parse_ttl_seconds(ttl_string):
    """Convert a Go duration string (e.g. '2h', '30m', '1h30m') to seconds."""
    total = 0
    for value, unit in re.findall(r"(\d+)([hms])", ttl_string):
        multiplier = {"h": 3600, "m": 60, "s": 1}[unit]
        total += int(value) * multiplier
    return total


def _parse_token_list(output):
    """Parse 'kubeadm token list' output into a dict keyed by token value.

    Returns: {token_value: {"ttl": str, "expires": str, "usages": str}}
    """
    tokens = {}
    lines = output.strip().splitlines()
    if len(lines) < 2:
        return tokens
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 3:
            continue
        token_value = parts[0]
        ttl = parts[1]
        expires = parts[2]
        tokens[token_value] = {"ttl": ttl, "expires": expires}
    return tokens


def _extract_token_from_join_content(content):
    """Pull the --token value out of a kubeadm join command string."""
    match = re.search(r"--token\s+([a-z0-9]{6}\.[a-z0-9]{16})", content)
    return match.group(1) if match else None


def check_kubernetes_worker_join_file_permissions(host):
    """Verify worker-join-command.sh has mode 600 and is owned by root."""
    summary = "Kubernetes worker join file permissions"
    try:
        _context_data, control, mount_point, _config = _resolve_mount_point(host)
        if control is None:
            return _skip(summary, "No Kubernetes nodes are mapped")
        file_path = _join_file_path(mount_point, _WORKER_JOIN_FILE)
        result = remote_command(
            host, control, PXEBOOT_COMMANDS["join_file_stat"] % file_path
        )
        if result.rc != 0:
            return runtime_result(
                False, summary,
                [("File", file_path), ("Error", result.stderr.strip())],
                f"Cannot stat {_WORKER_JOIN_FILE}: {result.stderr.strip()}",
            )
        stat_output = result.stdout.strip()
        parts = stat_output.split()
        mode, owner, group = (parts + ["", "", ""])[:3]
        ok = mode == "600" and owner == "root" and group == "root"
        fields = [
            ("File", file_path),
            ("Mode", mode),
            ("Owner", owner),
            ("Group", group),
            ("Expected", "600 root root"),
        ]
        return runtime_result(
            ok, summary, fields,
            f"{_WORKER_JOIN_FILE} permissions are {mode} {owner}:{group}, expected 600 root:root"
            if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_kubernetes_cp_join_file_permissions(host):
    """Verify control-plane-join-command.sh has mode 600 and is owned by root."""
    summary = "Kubernetes control-plane join file permissions"
    try:
        _context_data, control, mount_point, _config = _resolve_mount_point(host)
        if control is None:
            return _skip(summary, "No Kubernetes nodes are mapped")
        file_path = _join_file_path(mount_point, _CP_JOIN_FILE)
        result = remote_command(
            host, control, PXEBOOT_COMMANDS["join_file_stat"] % file_path
        )
        if result.rc != 0:
            return runtime_result(
                False, summary,
                [("File", file_path), ("Error", result.stderr.strip())],
                f"Cannot stat {_CP_JOIN_FILE}: {result.stderr.strip()}",
            )
        stat_output = result.stdout.strip()
        parts = stat_output.split()
        mode, owner, group = (parts + ["", "", ""])[:3]
        ok = mode == "600" and owner == "root" and group == "root"
        fields = [
            ("File", file_path),
            ("Mode", mode),
            ("Owner", owner),
            ("Group", group),
            ("Expected", "600 root root"),
        ]
        return runtime_result(
            ok, summary, fields,
            f"{_CP_JOIN_FILE} permissions are {mode} {owner}:{group}, expected 600 root:root"
            if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_kubernetes_worker_join_file_format(host):
    """Verify worker join file contains exactly one line matching the worker regex.

    Also asserts the file does NOT match the control-plane regex — the worker
    validator uses a strict $ anchor that rejects the extra --control-plane flags.
    """
    summary = "Kubernetes worker join file format"
    try:
        _context_data, control, mount_point, _config = _resolve_mount_point(host)
        if control is None:
            return _skip(summary, "No Kubernetes nodes are mapped")
        file_path = _join_file_path(mount_point, _WORKER_JOIN_FILE)

        line_result = remote_command(
            host, control, PXEBOOT_COMMANDS["join_file_line_count"] % file_path
        )
        line_count = int(line_result.stdout.strip()) if line_result.rc == 0 else -1

        content_result = remote_command(
            host, control, PXEBOOT_COMMANDS["join_file_content"] % file_path
        )
        content = content_result.stdout.strip() if content_result.rc == 0 else ""

        matches_worker = bool(_WORKER_JOIN_RE.match(content))
        matches_cp = bool(_CP_JOIN_RE.match(content))

        ok = line_count == 1 and matches_worker and not matches_cp
        fields = [
            ("File", file_path),
            ("Line count", line_count),
            ("Matches worker regex", "✓" if matches_worker else "✗"),
            ("Rejected by CP regex", "✓" if not matches_cp else "✗ (CP flags present — wrong file)"),
        ]
        errors = []
        if line_count != 1:
            errors.append(f"expected 1 line, got {line_count}")
        if not matches_worker:
            errors.append("content does not match worker kubeadm join format")
        if matches_cp:
            errors.append("content contains --control-plane flags, wrong file written")
        return runtime_result(ok, summary, fields, "; ".join(errors) if errors else "")
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_kubernetes_cp_join_file_format(host):
    """Verify CP join file contains exactly one line matching the CP regex.

    Also asserts the file does NOT match the worker regex — the worker regex
    rejects the extra --control-plane and --certificate-key flags via $ anchor.
    """
    summary = "Kubernetes control-plane join file format"
    try:
        _context_data, control, mount_point, _config = _resolve_mount_point(host)
        if control is None:
            return _skip(summary, "No Kubernetes nodes are mapped")
        file_path = _join_file_path(mount_point, _CP_JOIN_FILE)

        line_result = remote_command(
            host, control, PXEBOOT_COMMANDS["join_file_line_count"] % file_path
        )
        line_count = int(line_result.stdout.strip()) if line_result.rc == 0 else -1

        content_result = remote_command(
            host, control, PXEBOOT_COMMANDS["join_file_content"] % file_path
        )
        content = content_result.stdout.strip() if content_result.rc == 0 else ""

        matches_cp = bool(_CP_JOIN_RE.match(content))
        matches_worker = bool(_WORKER_JOIN_RE.match(content))

        ok = line_count == 1 and matches_cp and not matches_worker
        fields = [
            ("File", file_path),
            ("Line count", line_count),
            ("Matches CP regex", "✓" if matches_cp else "✗"),
            ("Rejected by worker regex", "✓" if not matches_worker else "✗ (missing CP flags)"),
        ]
        errors = []
        if line_count != 1:
            errors.append(f"expected 1 line, got {line_count}")
        if not matches_cp:
            errors.append("content does not match control-plane kubeadm join format")
        if matches_worker:
            errors.append("content matches only worker format, --control-plane flags missing")
        return runtime_result(ok, summary, fields, "; ".join(errors) if errors else "")
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_kubernetes_bootstrap_token_ttl(host):
    """Run the refresh script and verify each new token has the configured TTL.

    Steps:
      1. Execute generate-control-plane-join.sh on the first control-plane node.
      2. Read both join files and extract the --token value from each.
      3. Run 'kubeadm token list' and look up each extracted token by value.
      4. Parse the EXPIRES timestamp for each token and assert:
         - EXPIRES is not '<forever>' (regression: old code used --ttl 0)
         - now < EXPIRES <= now + configured_ttl + tolerance
    """
    summary = "Kubernetes bootstrap token TTL"
    try:
        context, control, mount_point, config = _resolve_mount_point(host)
        if control is None:
            return _skip(summary, "No Kubernetes nodes are mapped")

        configured_ttl_str = str(config.get("k8s_bootstrap_token_ttl", "2h")).strip()
        configured_ttl_seconds = _parse_ttl_seconds(configured_ttl_str)

        refresh_script = _join_file_path(mount_point, _REFRESH_SCRIPT)
        run_result = remote_command(
            host, control, PXEBOOT_COMMANDS["join_refresh_script"] % refresh_script
        )
        if run_result.rc != 0:
            return runtime_result(
                False, summary,
                [("Refresh script", refresh_script),
                 ("Exit code", run_result.rc),
                 ("Output", run_result.stdout.strip()[-300:])],
                f"Refresh script failed (rc={run_result.rc})",
            )

        worker_content_result = remote_command(
            host, control,
            PXEBOOT_COMMANDS["join_file_content"] % _join_file_path(mount_point, _WORKER_JOIN_FILE),
        )
        cp_content_result = remote_command(
            host, control,
            PXEBOOT_COMMANDS["join_file_content"] % _join_file_path(mount_point, _CP_JOIN_FILE),
        )

        worker_content = worker_content_result.stdout.strip()
        cp_content = cp_content_result.stdout.strip()

        worker_token = _extract_token_from_join_content(worker_content)
        cp_token = _extract_token_from_join_content(cp_content)

        if not worker_token:
            return runtime_result(
                False, summary,
                [("Worker join file", _WORKER_JOIN_FILE)],
                f"Could not extract --token from {_WORKER_JOIN_FILE}",
            )
        if not cp_token:
            return runtime_result(
                False, summary,
                [("CP join file", _CP_JOIN_FILE)],
                f"Could not extract --token from {_CP_JOIN_FILE}",
            )

        token_list_result = remote_command(
            host, control, PXEBOOT_COMMANDS["kubeadm_token_list"]
        )
        if token_list_result.rc != 0:
            return runtime_result(
                False, summary,
                [("kubeadm token list", "failed"), ("Error", token_list_result.stderr.strip())],
                "kubeadm token list command failed",
            )

        token_map = _parse_token_list(token_list_result.stdout)
        now = datetime.now(timezone.utc)
        fields = [
            ("Configured TTL", configured_ttl_str),
            ("Refresh script", refresh_script),
        ]
        errors = []

        for label, token_value in (("Worker", worker_token), ("Control-plane", cp_token)):
            if token_value not in token_map:
                fields.append((f"{label} token ({token_value})", "✗ not found in token list"))
                errors.append(f"{label} token {token_value} not found in kubeadm token list")
                continue

            entry = token_map[token_value]
            expires_str = entry["expires"]

            if expires_str in ("<forever>", "<none>", ""):
                fields.append((f"{label} token ({token_value})", f"✗ expires={expires_str} (permanent token)"))
                errors.append(f"{label} token has no expiry — --ttl 0 regression detected")
                continue

            try:
                expires_dt = datetime.fromisoformat(
                    expires_str.replace("Z", "+00:00")
                )
            except ValueError:
                fields.append((f"{label} token ({token_value})", f"✗ cannot parse EXPIRES={expires_str!r}"))
                errors.append(f"{label} token EXPIRES timestamp is not parseable: {expires_str!r}")
                continue

            remaining_seconds = (expires_dt - now).total_seconds()
            within_window = 0 < remaining_seconds <= configured_ttl_seconds + _TTL_TOLERANCE_SECONDS
            fields.append((
                f"{label} token ({token_value})",
                f"{'✓' if within_window else '✗'} expires={expires_str} "
                f"(~{int(remaining_seconds)}s remaining, configured={configured_ttl_str})",
            ))
            if not within_window:
                errors.append(
                    f"{label} token remaining TTL {int(remaining_seconds)}s is outside "
                    f"expected window (0, {configured_ttl_seconds + _TTL_TOLERANCE_SECONDS}]"
                )

        return runtime_result(not errors, summary, fields, "; ".join(errors) if errors else "")
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
