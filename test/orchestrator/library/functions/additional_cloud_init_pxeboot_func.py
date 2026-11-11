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

"""Additional cloud-init post-boot verification for stateless nodes."""

import os
import shlex

import yaml

from ..vars.pxeboot_vars import PXEBOOT_COMMANDS
from ..vars.provision_vars import ADDITIONAL_METADATA_PREFIX
from ._pxeboot_helpers import (
    remote_command,
    runtime_exception,
    runtime_result,
)
from ._prepare_helpers import read_yaml_mapping
from ._provision_helpers import (
    api_json,
    load_context,
    metadata_name,
    resource_list,
)
from ._workload_helpers import optional_skip as _skip


def _load_cloud_init_context(host):
    """Load provision context with orchestrator_config.

    Uses load_context (provision-level) instead of load_runtime_context
    so that orchestrator_status.yml is not required. Test ordering
    (pytest.mark.order 295-298) ensures these run after PXE boot tests.
    """
    context = load_context(host)
    input_dir = os.path.dirname(context["mapping_path"])
    context["orchestrator_config"] = read_yaml_mapping(
        host, os.path.join(input_dir, "orchestrator_config.yml"),
    )
    return context


def _load_additional_cloud_init_config(host, context):
    """Read the additional_cloud_init YAML from the OIM input directory.

    Returns (enabled, config_data, config_path) where config_data is the
    parsed YAML dict (with 'common' and/or 'groups' keys).
    """
    orchestrator_config = context.get("orchestrator_config", {})
    aci_path = str(
        orchestrator_config.get("additional_cloud_init_config_file") or ""
    ).strip()
    if not aci_path:
        return False, {}, ""
    remote = host.file(aci_path)
    if not remote.is_file:
        raise ValueError(
            f"additional_cloud_init_config_file not found: {aci_path}"
        )
    try:
        config_data = yaml.safe_load(remote.content_string) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {aci_path}: {exc}") from exc
    if not isinstance(config_data, dict):
        raise TypeError(f"Expected a YAML mapping in {aci_path}")
    common = config_data.get("common") or {}
    groups = config_data.get("groups") or {}
    enabled = bool(common) or bool(groups)
    return enabled, config_data, aci_path


def check_additional_cloud_init_smd_groups(host):
    """Verify SMD groups exist for additional cloud-init configuration."""
    summary = "Additional cloud-init SMD groups"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        common_data = config_data.get("common") or {}
        groups_data = config_data.get("groups") or {}

        # Load live SMD groups via API
        smd_groups = api_json(host, "smd_groups")
        smd_group_list = resource_list(smd_groups)
        if isinstance(smd_groups, dict) and "Groups" in smd_groups:
            smd_group_list = resource_list(smd_groups, "Groups")
        smd_labels = set()
        for item in smd_group_list:
            label = str(item.get("label") or "").strip()
            if label:
                smd_labels.add(label)

        failures = []
        fields = [
            ("Config file", aci_path),
            ("Common section", "present" if common_data else "empty"),
            ("Groups section", f"{len(groups_data)} FG(s)" if groups_data else "empty"),
            ("SMD groups found", len(smd_labels)),
        ]

        # Check common group exists if common section has content
        if common_data:
            expected_common = ADDITIONAL_METADATA_PREFIX
            if expected_common in smd_labels:
                fields.append(
                    ("  Common group", f"✓ {expected_common}")
                )
            else:
                failures.append(
                    f"Common SMD group '{expected_common}' not found"
                )
                fields.append(
                    ("  Common group", f"✗ {expected_common} MISSING")
                )

        # Check per-FG groups exist
        for fg_name in groups_data:
            fg_section = groups_data[fg_name]
            if not fg_section:
                continue
            expected_fg = f"{ADDITIONAL_METADATA_PREFIX}_{fg_name}"
            if expected_fg in smd_labels:
                fields.append(("  FG group", f"✓ {expected_fg}"))
            else:
                failures.append(
                    f"Per-FG SMD group '{expected_fg}' not found"
                )
                fields.append(("  FG group", f"✗ {expected_fg} MISSING"))

        return runtime_result(
            not failures,
            summary,
            fields,
            "; ".join(failures),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "Additional cloud-init SMD groups could not be validated", exc
        )


def check_additional_cloud_init_metadata_groups(host):
    """Verify metadata-service groups exist for additional cloud-init."""
    summary = "Additional cloud-init metadata-service groups"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        common_data = config_data.get("common") or {}
        groups_data = config_data.get("groups") or {}

        metadata_groups = resource_list(api_json(host, "metadata_groups"))
        metadata_names = {metadata_name(item) for item in metadata_groups}

        failures = []
        fields = [
            ("Config file", aci_path),
            ("Metadata-service groups", len(metadata_groups)),
        ]

        # Check common metadata group
        if common_data:
            expected = ADDITIONAL_METADATA_PREFIX
            matches = [
                item for item in metadata_groups
                if metadata_name(item) == expected
            ]
            if len(matches) == 1:
                spec = matches[0].get("spec") or {}
                template = str(spec.get("template") or "").strip()
                status = matches[0].get("status") or {}
                valid = bool(template) and status.get("valid") is not False
                fields.append(
                    (
                        "  Common template",
                        f"✓ valid ({len(template)} chars)"
                        if valid
                        else "✗ invalid or empty",
                    )
                )
                if not valid:
                    failures.append(
                        f"Common metadata group '{expected}' has invalid template"
                    )
            elif len(matches) == 0:
                failures.append(
                    f"Common metadata group '{expected}' not found"
                )
                fields.append(("  Common template", f"✗ {expected} MISSING"))
            else:
                failures.append(
                    f"Common metadata group '{expected}' count={len(matches)}"
                )
                fields.append(
                    ("  Common template", f"✗ {expected} duplicated")
                )

        # Check per-FG metadata groups
        for fg_name in groups_data:
            fg_section = groups_data[fg_name]
            if not fg_section:
                continue
            expected = f"{ADDITIONAL_METADATA_PREFIX}_{fg_name}"
            matches = [
                item for item in metadata_groups
                if metadata_name(item) == expected
            ]
            if len(matches) == 1:
                spec = matches[0].get("spec") or {}
                template = str(spec.get("template") or "").strip()
                status = matches[0].get("status") or {}
                valid = bool(template) and status.get("valid") is not False
                fields.append(
                    (
                        f"  FG template ({fg_name})",
                        f"✓ valid ({len(template)} chars)"
                        if valid
                        else "✗ invalid or empty",
                    )
                )
                if not valid:
                    failures.append(
                        f"FG metadata group '{expected}' has invalid template"
                    )
            elif len(matches) == 0:
                failures.append(
                    f"FG metadata group '{expected}' not found"
                )
                fields.append(
                    (f"  FG template ({fg_name})", f"✗ {expected} MISSING")
                )
            else:
                failures.append(
                    f"FG metadata group '{expected}' count={len(matches)}"
                )
                fields.append(
                    (f"  FG template ({fg_name})", f"✗ {expected} duplicated")
                )

        return runtime_result(
            not failures,
            summary,
            fields,
            "; ".join(failures),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "Additional cloud-init metadata groups could not be validated", exc
        )


def check_additional_cloud_init_write_files(host):
    """Verify write_files entries were applied on provisioned nodes."""
    summary = "Additional cloud-init write_files on nodes"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        common_data = config_data.get("common") or {}
        groups_data = config_data.get("groups") or {}

        # Collect expected write_files entries per scope
        common_files = []
        for entry in common_data.get("write_files") or []:
            if isinstance(entry, dict) and entry.get("path"):
                common_files.append(entry["path"])

        fg_files = {}
        for fg_name, fg_section in groups_data.items():
            if not isinstance(fg_section, dict):
                continue
            for entry in fg_section.get("write_files") or []:
                if isinstance(entry, dict) and entry.get("path"):
                    fg_files.setdefault(fg_name, []).append(entry["path"])

        if not common_files and not fg_files:
            return _skip(summary, "No write_files entries in config")

        rows = context["rows"]
        failures = []
        fields = [
            ("Config file", aci_path),
            ("Common write_files", len(common_files)),
            ("Per-FG write_files groups", len(fg_files)),
        ]

        # Check common write_files on all nodes
        verified = 0
        for row in rows:
            node_errors = []
            for filepath in common_files:
                result = remote_command(
                    host, row,
                    PXEBOOT_COMMANDS["cloud_init_file_check"]
                    % shlex.quote(filepath),
                )
                if result.rc != 0 or "EXISTS" not in result.stdout:
                    node_errors.append(f"{filepath} not found")
            if node_errors:
                failures.append(
                    f"{row['HOSTNAME']}: {'; '.join(node_errors)}"
                )
                fields.append(
                    (f"  {row['HOSTNAME']}", f"✗ {'; '.join(node_errors)}")
                )
            else:
                verified += 1

        if common_files:
            fields.append(("  Common files verified", f"{verified}/{len(rows)}"))

        # Check per-FG write_files on matching nodes
        for fg_name, file_paths in fg_files.items():
            matching_rows = [
                row for row in rows
                if row.get("FUNCTIONAL_GROUP_NAME", "") == fg_name
            ]
            if not matching_rows:
                failures.append(
                    f"FG {fg_name}: no matching nodes in PXE mapping"
                )
                fields.append(
                    (f"  FG {fg_name} write_files", "✗ no matching nodes")
                )
                continue
            fg_verified = 0
            for row in matching_rows:
                node_errors = []
                for filepath in file_paths:
                    result = remote_command(
                        host, row,
                        PXEBOOT_COMMANDS["cloud_init_file_check"]
                        % shlex.quote(filepath),
                    )
                    if result.rc != 0 or "EXISTS" not in result.stdout:
                        node_errors.append(f"{filepath} not found")
                if node_errors:
                    failures.append(
                        f"{row['HOSTNAME']}({fg_name}): {'; '.join(node_errors)}"
                    )
                    fields.append(
                        (
                            f"  {row['HOSTNAME']}({fg_name})",
                            f"✗ {'; '.join(node_errors)}",
                        )
                    )
                else:
                    fg_verified += 1
            fields.append(
                (
                    f"  FG {fg_name} files verified",
                    f"{fg_verified}/{len(matching_rows)}",
                )
            )

        return runtime_result(
            not failures,
            summary,
            fields,
            "; ".join(failures),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "Additional cloud-init write_files could not be validated", exc
        )


def _extract_runcmd_log_paths(commands):
    """Extract log file paths from runcmd entries that use >> redirection.

    Returns a list of file paths that runcmd entries append to.  This lets
    the test verify runcmd execution by checking whether those files exist
    on the node — a more direct check than parsing cloud-init status JSON.
    """
    paths = []
    for cmd in commands:
        if not isinstance(cmd, str):
            continue
        # Match: ... >> /path/to/file or ... >> /path/to/file (end)
        parts = cmd.split(">>")
        if len(parts) >= 2:
            target = parts[-1].strip().split()[0]
            if target.startswith("/"):
                paths.append(target)
    return paths


def check_additional_cloud_init_runcmd(host):
    """Verify runcmd entries executed during cloud-init on provisioned nodes.

    Checks for runcmd execution by verifying that log files produced by
    the configured runcmd entries exist on the target nodes.  Falls back
    to cloud-init status when no verifiable log paths can be extracted.
    """
    summary = "Additional cloud-init runcmd on nodes"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        common_data = config_data.get("common") or {}
        groups_data = config_data.get("groups") or {}

        common_cmds = common_data.get("runcmd") or []
        if not isinstance(common_cmds, list):
            common_cmds = []

        fg_cmds = {}
        for fg_name, fg_section in groups_data.items():
            if not isinstance(fg_section, dict):
                continue
            cmds = fg_section.get("runcmd") or []
            if isinstance(cmds, list) and cmds:
                fg_cmds[fg_name] = cmds

        if not common_cmds and not fg_cmds:
            return _skip(summary, "No runcmd entries in config")

        # Extract verifiable log paths from runcmd entries
        common_log_paths = _extract_runcmd_log_paths(common_cmds)
        fg_log_paths = {
            fg: _extract_runcmd_log_paths(cmds) for fg, cmds in fg_cmds.items()
        }

        rows = context["rows"]
        failures = []
        fields = [
            ("Config file", aci_path),
            ("Common runcmd entries", len(common_cmds)),
            ("Common verifiable logs", len(common_log_paths)),
            ("Per-FG runcmd groups", len(fg_cmds)),
        ]

        # Check common runcmd log files on all nodes
        verified = 0
        for row in rows:
            node_errors = []
            if common_log_paths:
                for log_path in common_log_paths:
                    result = remote_command(
                        host, row,
                        PXEBOOT_COMMANDS["cloud_init_file_check"]
                        % shlex.quote(log_path),
                    )
                    if result.rc != 0 or "EXISTS" not in result.stdout:
                        node_errors.append(f"{log_path} not found")
            else:
                # No verifiable log paths; fall back to cloud-init status
                result = remote_command(
                    host, row, PXEBOOT_COMMANDS["cloud_init_status"],
                )
                if result.rc != 0:
                    node_errors.append("cloud-init status unavailable")
                elif "done" not in result.stdout.lower():
                    node_errors.append("cloud-init not done")

            if node_errors:
                failures.append(
                    f"{row['HOSTNAME']}: {'; '.join(node_errors)}"
                )
                fields.append(
                    (f"  {row['HOSTNAME']}", f"✗ {'; '.join(node_errors)}")
                )
            else:
                verified += 1
                fields.append(
                    (f"  {row['HOSTNAME']}", "✓ runcmd artifacts verified")
                )

        fields.append(("  Common runcmd verified", f"{verified}/{len(rows)}"))

        # Load metadata templates so command presence can be verified
        # when no log-path artifact is available.
        metadata_groups = resource_list(api_json(host, "metadata_groups"))
        fg_templates = {}
        for fg_name in fg_log_paths:
            expected = f"{ADDITIONAL_METADATA_PREFIX}_{fg_name}"
            matches = [
                item for item in metadata_groups
                if metadata_name(item) == expected
            ]
            if matches:
                spec = matches[0].get("spec") or {}
                fg_templates[fg_name] = str(spec.get("template") or "")

        # Check per-FG runcmd on matching nodes
        for fg_name, log_paths in fg_log_paths.items():
            matching_rows = [
                row for row in rows
                if row.get("FUNCTIONAL_GROUP_NAME", "") == fg_name
            ]
            if not matching_rows:
                failures.append(
                    f"FG {fg_name}: no matching nodes in PXE mapping"
                )
                fields.append(
                    (f"  FG {fg_name}", "✗ no matching nodes")
                )
                continue
            fg_verified = 0
            for row in matching_rows:
                node_errors = []
                if log_paths:
                    for log_path in log_paths:
                        result = remote_command(
                            host, row,
                            PXEBOOT_COMMANDS["cloud_init_file_check"]
                            % shlex.quote(log_path),
                        )
                        if result.rc != 0 or "EXISTS" not in result.stdout:
                            node_errors.append(f"{log_path} not found")
                else:
                    # No extractable log paths; verify the configured
                    # commands are present in the rendered metadata template
                    # and that cloud-init completed on this node.
                    template = fg_templates.get(fg_name, "")
                    for cmd in fg_cmds.get(fg_name, []):
                        if isinstance(cmd, str) and cmd not in template:
                            node_errors.append(
                                f"command not in metadata template: "
                                f"{cmd[:80]}"
                            )
                    if not node_errors:
                        result = remote_command(
                            host, row, PXEBOOT_COMMANDS["cloud_init_status"],
                        )
                        if result.rc != 0:
                            node_errors.append("cloud-init status unavailable")
                        elif "done" not in result.stdout.lower():
                            node_errors.append("cloud-init not done")
                if node_errors:
                    failures.append(
                        f"{row['HOSTNAME']}({fg_name}): {'; '.join(node_errors)}"
                    )
                    fields.append(
                        (
                            f"  {row['HOSTNAME']}({fg_name})",
                            f"✗ {'; '.join(node_errors)}",
                        )
                    )
                else:
                    fg_verified += 1
            fields.append(
                (
                    f"  FG {fg_name} runcmd verified",
                    f"{fg_verified}/{len(matching_rows)}",
                )
            )

        return runtime_result(
            not failures,
            summary,
            fields,
            "; ".join(failures),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "Additional cloud-init runcmd could not be validated", exc
        )
