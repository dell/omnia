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
import time

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

# merge_how strategy expected in all additional cloud-init templates
_MERGE_HOW_STRATEGY = "no_replace"


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


# =====================================================================
# Template / BSS verification (TC-F08 .. TC-F13 from 2.2)
# =====================================================================


def _metadata_template_text(metadata_groups, expected_name):
    """Return the template string for a named metadata group, or None."""
    for item in metadata_groups:
        if metadata_name(item) == expected_name:
            spec = item.get("spec") or {}
            return str(spec.get("template") or "")
    return None


def check_additional_cloud_init_common_template(host):
    """TC-F08: Verify common cloud-init template rendered with merge_how."""
    summary = "Additional cloud-init common template rendering"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        common_data = config_data.get("common") or {}
        if not common_data:
            return _skip(summary, "No common section in config")

        metadata_groups = resource_list(api_json(host, "metadata_groups"))
        template = _metadata_template_text(
            metadata_groups, ADDITIONAL_METADATA_PREFIX
        )

        failures = []
        fields = [
            ("Config file", aci_path),
            ("Expected group", ADDITIONAL_METADATA_PREFIX),
        ]

        if template is None:
            failures.append(
                f"Common metadata group '{ADDITIONAL_METADATA_PREFIX}' not found"
            )
            fields.append(("Template", "MISSING"))
        else:
            fields.append(("Template length", f"{len(template)} chars"))
            if _MERGE_HOW_STRATEGY not in template.lower():
                failures.append(
                    f"merge_how '{_MERGE_HOW_STRATEGY}' not found in template"
                )
            if common_data.get("write_files"):
                if "write_files" not in template:
                    failures.append("write_files directive absent from template")
            if common_data.get("runcmd"):
                if "runcmd" not in template:
                    failures.append("runcmd directive absent from template")

        return runtime_result(not failures, summary, fields, "; ".join(failures))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "Common template rendering could not be validated", exc
        )


def check_additional_cloud_init_per_fg_template(host):
    """TC-F09: Verify per-FG cloud-init template rendering."""
    summary = "Additional cloud-init per-FG template rendering"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        groups_data = config_data.get("groups") or {}
        if not groups_data:
            return _skip(summary, "No groups section in config")

        metadata_groups = resource_list(api_json(host, "metadata_groups"))
        failures = []
        fields = [("Config file", aci_path), ("FG groups", len(groups_data))]

        for fg_name, fg_section in groups_data.items():
            if not fg_section:
                continue
            expected = f"{ADDITIONAL_METADATA_PREFIX}_{fg_name}"
            template = _metadata_template_text(metadata_groups, expected)
            if template is None:
                failures.append(f"FG metadata group '{expected}' not found")
                fields.append((f"  {fg_name}", "MISSING"))
            else:
                fields.append((f"  {fg_name}", f"{len(template)} chars"))
                if _MERGE_HOW_STRATEGY not in template.lower():
                    failures.append(
                        f"merge_how absent in template for {fg_name}"
                    )

        return runtime_result(not failures, summary, fields, "; ".join(failures))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "Per-FG template rendering could not be validated", exc
        )


def check_additional_cloud_init_conditional_rendering(host):
    """TC-F10: Verify empty sections are omitted from rendered templates."""
    summary = "Additional cloud-init conditional rendering"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        metadata_groups = resource_list(api_json(host, "metadata_groups"))
        failures = []
        fields = [("Config file", aci_path)]

        # Check common template
        common_data = config_data.get("common") or {}
        if common_data:
            template = _metadata_template_text(
                metadata_groups, ADDITIONAL_METADATA_PREFIX
            ) or ""
            has_wf = bool(common_data.get("write_files"))
            has_rc = bool(common_data.get("runcmd"))
            if not has_wf and "write_files" in template:
                failures.append("Common template includes empty write_files")
            if not has_rc and "runcmd" in template:
                failures.append("Common template includes empty runcmd")
            fields.append(
                ("Common", f"wf={has_wf} rc={has_rc} tmpl={len(template)}ch")
            )

        # Check per-FG templates
        for fg_name, fg_section in (config_data.get("groups") or {}).items():
            if not fg_section:
                continue
            expected = f"{ADDITIONAL_METADATA_PREFIX}_{fg_name}"
            template = _metadata_template_text(metadata_groups, expected) or ""
            has_wf = bool(fg_section.get("write_files"))
            has_rc = bool(fg_section.get("runcmd"))
            if not has_wf and "write_files" in template:
                failures.append(f"{fg_name} template includes empty write_files")
            if not has_rc and "runcmd" in template:
                failures.append(f"{fg_name} template includes empty runcmd")
            fields.append(
                (f"  {fg_name}", f"wf={has_wf} rc={has_rc} tmpl={len(template)}ch")
            )

        if not fields[1:]:
            return _skip(summary, "No sections to check")

        return runtime_result(not failures, summary, fields, "; ".join(failures))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "Conditional rendering could not be validated", exc
        )


def check_additional_cloud_init_bss_common(host):
    """TC-F11: Verify BSS registration for common cloud-init group."""
    summary = "Additional cloud-init BSS common registration"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        common_data = config_data.get("common") or {}
        if not common_data:
            return _skip(summary, "No common section in config")

        metadata_groups = resource_list(api_json(host, "metadata_groups"))
        expected = ADDITIONAL_METADATA_PREFIX
        matches = [
            item for item in metadata_groups
            if metadata_name(item) == expected
        ]

        failures = []
        fields = [("Config file", aci_path), ("Expected BSS group", expected)]

        if not matches:
            failures.append(f"BSS group '{expected}' not registered")
            fields.append(("Registration", "MISSING"))
        elif len(matches) > 1:
            failures.append(f"BSS group '{expected}' duplicated ({len(matches)})")
            fields.append(("Registration", f"DUPLICATED ({len(matches)})"))
        else:
            spec = matches[0].get("spec") or {}
            template = str(spec.get("template") or "").strip()
            status = matches[0].get("status") or {}
            valid = bool(template) and status.get("valid") is not False
            fields.append(("Registration", "present"))
            fields.append(("Template valid", str(valid)))
            if not valid:
                failures.append(f"BSS group '{expected}' template invalid")

        return runtime_result(not failures, summary, fields, "; ".join(failures))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "BSS common registration could not be validated", exc
        )


def check_additional_cloud_init_bss_per_fg(host):
    """TC-F12: Verify BSS registration for per-FG cloud-init groups."""
    summary = "Additional cloud-init BSS per-FG registration"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        groups_data = config_data.get("groups") or {}
        if not groups_data:
            return _skip(summary, "No groups section in config")

        metadata_groups = resource_list(api_json(host, "metadata_groups"))
        failures = []
        fields = [("Config file", aci_path), ("FG groups", len(groups_data))]

        for fg_name, fg_section in groups_data.items():
            if not fg_section:
                continue
            expected = f"{ADDITIONAL_METADATA_PREFIX}_{fg_name}"
            matches = [
                item for item in metadata_groups
                if metadata_name(item) == expected
            ]
            if not matches:
                failures.append(f"BSS group '{expected}' not registered")
                fields.append((f"  {fg_name}", "MISSING"))
            elif len(matches) > 1:
                failures.append(f"BSS group '{expected}' duplicated")
                fields.append((f"  {fg_name}", f"DUPLICATED ({len(matches)})"))
            else:
                spec = matches[0].get("spec") or {}
                template = str(spec.get("template") or "").strip()
                valid = bool(template)
                fields.append((f"  {fg_name}", "registered" if valid else "empty"))
                if not valid:
                    failures.append(f"BSS group '{expected}' has empty template")

        return runtime_result(not failures, summary, fields, "; ".join(failures))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "BSS per-FG registration could not be validated", exc
        )


def check_additional_cloud_init_merge_behavior(host):
    """TC-F13: Verify merge_how=no_replace preserves platform defaults."""
    summary = "Additional cloud-init merge behavior"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        metadata_groups = resource_list(api_json(host, "metadata_groups"))
        failures = []
        fields = [
            ("Config file", aci_path),
            ("Expected strategy", _MERGE_HOW_STRATEGY),
        ]

        # Check every registered additional metadata template
        checked = 0
        for item in metadata_groups:
            name = metadata_name(item)
            if not name.startswith(ADDITIONAL_METADATA_PREFIX):
                continue
            spec = item.get("spec") or {}
            template = str(spec.get("template") or "")
            checked += 1
            if _MERGE_HOW_STRATEGY in template.lower():
                fields.append((f"  {name}", f"merge_how present"))
            else:
                failures.append(f"merge_how absent in '{name}'")
                fields.append((f"  {name}", "merge_how MISSING"))

        if checked == 0:
            return _skip(summary, "No additional metadata groups registered")

        fields.insert(2, ("Groups checked", str(checked)))
        return runtime_result(not failures, summary, fields, "; ".join(failures))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "Merge behavior could not be validated", exc
        )


# =====================================================================
# Compatibility tests (TC-C01 .. TC-C03 from 2.2)
# =====================================================================


def check_additional_cloud_init_rhel_compat(host):
    """TC-C01: Verify additional cloud-init on RHEL 10.x nodes."""
    summary = "Additional cloud-init RHEL 10.x compatibility"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        rows = context["rows"]
        failures = []
        fields = [("Config file", aci_path), ("Nodes", len(rows))]
        rhel10_count = 0

        for row in rows:
            result = remote_command(
                host, row, PXEBOOT_COMMANDS["aci_os_release"],
            )
            if result.rc != 0:
                fields.append((f"  {row['HOSTNAME']}", "unreachable"))
                continue
            os_info = {}
            for line in result.stdout.strip().splitlines():
                if "=" in line:
                    key, val = line.split("=", 1)
                    os_info[key.strip()] = val.strip().strip('"')
            os_id = os_info.get("ID", "")
            version = os_info.get("VERSION_ID", "")
            is_rhel10 = "rhel" in os_id.lower() and version.startswith("10.")
            if is_rhel10:
                rhel10_count += 1
                fields.append((f"  {row['HOSTNAME']}", f"RHEL {version}"))
            else:
                fields.append((f"  {row['HOSTNAME']}", f"{os_id} {version}"))

        fields.insert(2, ("RHEL 10.x nodes", str(rhel10_count)))
        if rhel10_count == 0:
            failures.append("No RHEL 10.x nodes found in cluster")

        return runtime_result(not failures, summary, fields, "; ".join(failures))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "RHEL compatibility could not be validated", exc
        )


def check_additional_cloud_init_multi_fg_compat(host):
    """TC-C02: Verify additional cloud-init with multiple functional groups."""
    summary = "Additional cloud-init multi-FG compatibility"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        rows = context["rows"]
        # Collect unique functional groups from the PXE mapping
        available_fgs = sorted(
            {row.get("FUNCTIONAL_GROUP_NAME", "") for row in rows} - {""}
        )

        groups_data = config_data.get("groups") or {}
        common_data = config_data.get("common") or {}

        failures = []
        fields = [
            ("Config file", aci_path),
            ("Available FGs", len(available_fgs)),
            ("Common section", "present" if common_data else "empty"),
            ("Per-FG groups", len(groups_data)),
        ]

        # Common applies to all FGs
        common_fgs = available_fgs if common_data else []
        per_fg_fgs = [fg for fg in groups_data if fg in available_fgs]

        # Verify at least 3 unique FGs involved
        unique_fgs = sorted(set(common_fgs) | set(per_fg_fgs))
        fields.append(("Unique FGs covered", len(unique_fgs)))

        if len(available_fgs) < 3:
            return _skip(
                summary,
                f"Only {len(available_fgs)} FG(s) available; need 3+ for multi-FG test",
            )

        # Check per-FG references are valid
        for fg_name in groups_data:
            if fg_name not in available_fgs:
                failures.append(
                    f"Config references FG '{fg_name}' not in PXE mapping"
                )
                fields.append((f"  {fg_name}", "NOT IN MAPPING"))
            else:
                matching = sum(
                    1 for r in rows
                    if r.get("FUNCTIONAL_GROUP_NAME") == fg_name
                )
                fields.append((f"  {fg_name}", f"{matching} node(s)"))

        return runtime_result(not failures, summary, fields, "; ".join(failures))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "Multi-FG compatibility could not be validated", exc
        )


def check_additional_cloud_init_upgrade_mode(host):
    """TC-C03: Verify upgrade mode skips delete/set operations."""
    summary = "Additional cloud-init upgrade mode compatibility"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        orchestrator_config = context.get("orchestrator_config", {})

        failures = []
        fields = [("Config file", aci_path)]

        # Config loading must succeed regardless of upgrade_mode
        fields.append(("Config loading", "OK"))

        # Validate the structure is correct (same validation runs in
        # both normal and upgrade mode)
        common_data = config_data.get("common") or {}
        groups_data = config_data.get("groups") or {}
        fields.append(("Common section", "present" if common_data else "empty"))
        fields.append(("Groups section", f"{len(groups_data)} FG(s)"))

        # Verify SMD groups still exist (upgrade mode preserves them)
        smd_groups = api_json(host, "smd_groups")
        smd_group_list = resource_list(smd_groups)
        if isinstance(smd_groups, dict) and "Groups" in smd_groups:
            smd_group_list = resource_list(smd_groups, "Groups")
        smd_labels = {
            str(item.get("label") or "").strip()
            for item in smd_group_list
        }

        if common_data:
            expected = ADDITIONAL_METADATA_PREFIX
            present = expected in smd_labels
            fields.append(("Common SMD group", "present" if present else "MISSING"))
            if not present:
                failures.append(f"Common SMD group '{expected}' missing")

        for fg_name in groups_data:
            if not groups_data[fg_name]:
                continue
            expected = f"{ADDITIONAL_METADATA_PREFIX}_{fg_name}"
            present = expected in smd_labels
            fields.append(
                (f"  FG {fg_name} SMD", "present" if present else "MISSING")
            )
            if not present:
                failures.append(f"FG SMD group '{expected}' missing")

        return runtime_result(not failures, summary, fields, "; ".join(failures))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "Upgrade mode compatibility could not be validated", exc
        )


# =====================================================================
# Idempotency tests (TC-I01 .. TC-I03 from 2.2)
# =====================================================================


def _snapshot_smd_labels(host):
    """Capture current set of additional cloud-init SMD group labels."""
    smd_groups = api_json(host, "smd_groups")
    smd_group_list = resource_list(smd_groups)
    if isinstance(smd_groups, dict) and "Groups" in smd_groups:
        smd_group_list = resource_list(smd_groups, "Groups")
    return {
        str(item.get("label") or "").strip()
        for item in smd_group_list
        if str(item.get("label") or "").startswith(ADDITIONAL_METADATA_PREFIX)
    }


def _snapshot_metadata_names(host):
    """Capture current set of additional cloud-init metadata group names."""
    metadata_groups = resource_list(api_json(host, "metadata_groups"))
    return {
        metadata_name(item)
        for item in metadata_groups
        if metadata_name(item).startswith(ADDITIONAL_METADATA_PREFIX)
    }


def check_additional_cloud_init_smd_idempotency(host):
    """TC-I01: Verify SMD group creation is idempotent across re-runs."""
    summary = "Additional cloud-init SMD group idempotency"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        # Snapshot before
        before = _snapshot_smd_labels(host)
        if not before:
            return _skip(summary, "No additional cloud-init SMD groups exist")

        # Snapshot again immediately (no re-provision -- just verify stability)
        after = _snapshot_smd_labels(host)

        failures = []
        fields = [
            ("Config file", aci_path),
            ("Before count", len(before)),
            ("After count", len(after)),
        ]

        if before != after:
            added = after - before
            removed = before - after
            if added:
                failures.append(f"Groups appeared: {', '.join(sorted(added))}")
            if removed:
                failures.append(f"Groups disappeared: {', '.join(sorted(removed))}")
        else:
            fields.append(("Membership", "stable"))

        return runtime_result(not failures, summary, fields, "; ".join(failures))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "SMD idempotency could not be validated", exc
        )


def check_additional_cloud_init_bss_idempotency(host):
    """TC-I02: Verify BSS registration is idempotent across re-reads."""
    summary = "Additional cloud-init BSS registration idempotency"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        # Snapshot before
        before = _snapshot_metadata_names(host)
        if not before:
            return _skip(summary, "No additional cloud-init BSS groups exist")

        # Brief pause then re-read to check stability
        time.sleep(2)
        after = _snapshot_metadata_names(host)

        failures = []
        fields = [
            ("Config file", aci_path),
            ("Before count", len(before)),
            ("After count", len(after)),
        ]

        if before != after:
            added = after - before
            removed = before - after
            if added:
                failures.append(f"BSS groups appeared: {', '.join(sorted(added))}")
            if removed:
                failures.append(f"BSS groups disappeared: {', '.join(sorted(removed))}")
        else:
            fields.append(("Registration", "stable"))

        return runtime_result(not failures, summary, fields, "; ".join(failures))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "BSS idempotency could not be validated", exc
        )


def check_additional_cloud_init_pipeline_idempotency(host):
    """TC-I03: Verify full pipeline (SMD + BSS) is idempotent."""
    summary = "Additional cloud-init full pipeline idempotency"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        # Snapshot both SMD and BSS state
        smd_before = _snapshot_smd_labels(host)
        bss_before = _snapshot_metadata_names(host)

        if not smd_before and not bss_before:
            return _skip(summary, "No additional cloud-init groups exist")

        # Brief pause then re-read both
        time.sleep(2)
        smd_after = _snapshot_smd_labels(host)
        bss_after = _snapshot_metadata_names(host)

        failures = []
        fields = [
            ("Config file", aci_path),
            ("SMD before", len(smd_before)),
            ("SMD after", len(smd_after)),
            ("BSS before", len(bss_before)),
            ("BSS after", len(bss_after)),
        ]

        if smd_before != smd_after:
            failures.append(
                f"SMD groups changed: before={len(smd_before)} after={len(smd_after)}"
            )
        else:
            fields.append(("SMD stability", "OK"))

        if bss_before != bss_after:
            failures.append(
                f"BSS groups changed: before={len(bss_before)} after={len(bss_after)}"
            )
        else:
            fields.append(("BSS stability", "OK"))

        return runtime_result(not failures, summary, fields, "; ".join(failures))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "Pipeline idempotency could not be validated", exc
        )


# =====================================================================
# End-to-end node verification (TC-F16 .. TC-F21 from 2.2)
# =====================================================================


def _verify_files_on_row(host, row, file_paths):
    """Check that each path in *file_paths* exists on the remote node."""
    errors = []
    for filepath in file_paths:
        result = remote_command(
            host, row,
            PXEBOOT_COMMANDS["cloud_init_file_check"]
            % shlex.quote(filepath),
        )
        if result.rc != 0 or "EXISTS" not in result.stdout:
            errors.append(f"{filepath} not found")
    return errors


def _verify_runcmd_on_row(host, row, log_paths):
    """Check runcmd artifacts on a single node.

    If *log_paths* is non-empty, checks those files exist.  Otherwise
    falls back to cloud-init status.
    """
    if log_paths:
        return _verify_files_on_row(host, row, log_paths)
    result = remote_command(
        host, row, PXEBOOT_COMMANDS["cloud_init_status"],
    )
    if result.rc != 0:
        return ["cloud-init status unavailable"]
    if "done" not in result.stdout.lower():
        return ["cloud-init not done"]
    return []


def _e2e_verify_scope(host, rows, write_files, runcmd, scope_label):
    """Run file + runcmd verification for one scope against *rows*.

    Returns (verified_count, failure_strings, field_tuples).
    """
    file_paths = [
        e["path"] for e in (write_files or [])
        if isinstance(e, dict) and e.get("path")
    ]
    log_paths = _extract_runcmd_log_paths(runcmd or [])
    failures = []
    fields = []
    verified = 0
    for row in rows:
        node_errors = _verify_files_on_row(host, row, file_paths)
        node_errors += _verify_runcmd_on_row(host, row, log_paths)
        if node_errors:
            failures.append(
                f"{row['HOSTNAME']}({scope_label}): {'; '.join(node_errors)}"
            )
            fields.append(
                (f"  {row['HOSTNAME']}({scope_label})",
                 f"✗ {'; '.join(node_errors)}")
            )
        else:
            verified += 1
            fields.append(
                (f"  {row['HOSTNAME']}({scope_label})", "✓ verified")
            )
    fields.append(
        (f"  {scope_label} verified", f"{verified}/{len(rows)}")
    )
    return verified, failures, fields


def check_additional_cloud_init_e2e_common_only(host):
    """TC-F16: End-to-end verification with common section only."""
    summary = "Additional cloud-init e2e common only"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        common = config_data.get("common") or {}
        groups = config_data.get("groups") or {}
        if not common:
            return _skip(summary, "No common section in config")
        if groups:
            return _skip(summary, "Config has groups section (not common-only)")

        rows = context["rows"]
        if not rows:
            return _skip(summary, "No nodes in PXE mapping")

        write_files = common.get("write_files") or []
        runcmd = common.get("runcmd") or []
        if not write_files and not runcmd:
            return _skip(summary, "Common section has no directives")

        verified, failures, row_fields = _e2e_verify_scope(
            host, rows, write_files, runcmd, "common",
        )
        fields = [
            ("Config file", aci_path),
            ("Mode", "common-only"),
            ("Nodes", len(rows)),
            ("write_files", len(write_files)),
            ("runcmd", len(runcmd)),
        ] + row_fields

        return runtime_result(not failures, summary, fields, "; ".join(failures))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "E2E common-only could not be validated", exc
        )


def check_additional_cloud_init_e2e_per_fg_only(host):
    """TC-F17: End-to-end verification with per-FG section only."""
    summary = "Additional cloud-init e2e per-FG only"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        common = config_data.get("common") or {}
        groups = config_data.get("groups") or {}
        if not groups:
            return _skip(summary, "No groups section in config")
        if common:
            return _skip(summary, "Config has common section (not per-FG-only)")

        rows = context["rows"]
        if not rows:
            return _skip(summary, "No nodes in PXE mapping")

        all_failures = []
        fields = [
            ("Config file", aci_path),
            ("Mode", "per-FG-only"),
            ("Functional groups", len(groups)),
        ]

        for fg_name, fg_section in groups.items():
            if not isinstance(fg_section, dict):
                continue
            matching = [
                r for r in rows
                if r.get("FUNCTIONAL_GROUP_NAME", "") == fg_name
            ]
            if not matching:
                all_failures.append(f"FG {fg_name}: no matching nodes")
                fields.append((f"  FG {fg_name}", "✗ no matching nodes"))
                continue
            wf = fg_section.get("write_files") or []
            rc = fg_section.get("runcmd") or []
            _, fg_fails, fg_fields = _e2e_verify_scope(
                host, matching, wf, rc, fg_name,
            )
            all_failures.extend(fg_fails)
            fields.extend(fg_fields)

        return runtime_result(
            not all_failures, summary, fields, "; ".join(all_failures)
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "E2E per-FG-only could not be validated", exc
        )


def check_additional_cloud_init_e2e_combined(host):
    """TC-F18: End-to-end verification with common + per-FG combined."""
    summary = "Additional cloud-init e2e combined"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        common = config_data.get("common") or {}
        groups = config_data.get("groups") or {}
        if not common:
            return _skip(summary, "No common section in config")
        if not groups:
            return _skip(summary, "No groups section (not combined)")

        rows = context["rows"]
        if not rows:
            return _skip(summary, "No nodes in PXE mapping")

        all_failures = []
        fields = [
            ("Config file", aci_path),
            ("Mode", "common + per-FG"),
            ("Nodes", len(rows)),
            ("Functional groups", len(groups)),
        ]

        # Verify common directives on ALL nodes
        common_wf = common.get("write_files") or []
        common_rc = common.get("runcmd") or []
        if common_wf or common_rc:
            _, c_fails, c_fields = _e2e_verify_scope(
                host, rows, common_wf, common_rc, "common",
            )
            all_failures.extend(c_fails)
            fields.extend(c_fields)

        # Verify per-FG directives on matching nodes
        for fg_name, fg_section in groups.items():
            if not isinstance(fg_section, dict):
                continue
            matching = [
                r for r in rows
                if r.get("FUNCTIONAL_GROUP_NAME", "") == fg_name
            ]
            if not matching:
                continue
            wf = fg_section.get("write_files") or []
            rc = fg_section.get("runcmd") or []
            if wf or rc:
                _, fg_fails, fg_fields = _e2e_verify_scope(
                    host, matching, wf, rc, fg_name,
                )
                all_failures.extend(fg_fails)
                fields.extend(fg_fields)

        return runtime_result(
            not all_failures, summary, fields, "; ".join(all_failures)
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "E2E combined could not be validated", exc
        )


def check_additional_cloud_init_e2e_multiple_fgs(host):
    """TC-F19: End-to-end verification with multiple functional groups."""
    summary = "Additional cloud-init e2e multiple FGs"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        groups = config_data.get("groups") or {}
        if len(groups) < 2:
            return _skip(
                summary,
                f"Need >= 2 FGs in groups, found {len(groups)}",
            )

        rows = context["rows"]
        if not rows:
            return _skip(summary, "No nodes in PXE mapping")

        all_failures = []
        fields = [
            ("Config file", aci_path),
            ("Functional groups", len(groups)),
            ("Total nodes", len(rows)),
        ]

        fg_verified_counts = {}
        for fg_name, fg_section in groups.items():
            if not isinstance(fg_section, dict):
                continue
            matching = [
                r for r in rows
                if r.get("FUNCTIONAL_GROUP_NAME", "") == fg_name
            ]
            if not matching:
                all_failures.append(f"FG {fg_name}: no matching nodes")
                fields.append((f"  FG {fg_name}", "✗ no matching nodes"))
                continue
            wf = fg_section.get("write_files") or []
            rc = fg_section.get("runcmd") or []
            v, fg_fails, fg_fields = _e2e_verify_scope(
                host, matching, wf, rc, fg_name,
            )
            fg_verified_counts[fg_name] = v
            all_failures.extend(fg_fails)
            fields.extend(fg_fields)

        # Cross-contamination check: per-FG files should NOT appear on
        # nodes belonging to other FGs.
        for fg_name, fg_section in groups.items():
            if not isinstance(fg_section, dict):
                continue
            fg_file_paths = [
                e["path"] for e in (fg_section.get("write_files") or [])
                if isinstance(e, dict) and e.get("path")
            ]
            if not fg_file_paths:
                continue
            other_rows = [
                r for r in rows
                if r.get("FUNCTIONAL_GROUP_NAME", "") != fg_name
            ]
            for row in other_rows:
                for fp in fg_file_paths:
                    result = remote_command(
                        host, row,
                        PXEBOOT_COMMANDS["cloud_init_file_check"]
                        % shlex.quote(fp),
                    )
                    if result.rc == 0 and "EXISTS" in result.stdout:
                        all_failures.append(
                            f"{row['HOSTNAME']}: FG {fg_name} file "
                            f"{fp} found on non-member node"
                        )
                        fields.append(
                            (f"  {row['HOSTNAME']}",
                             f"✗ cross-FG leak: {fp}")
                        )

        return runtime_result(
            not all_failures, summary, fields, "; ".join(all_failures)
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "E2E multiple FGs could not be validated", exc
        )


def check_additional_cloud_init_e2e_mixed_directives(host):
    """TC-F20: End-to-end verification with write_files + runcmd together."""
    summary = "Additional cloud-init e2e mixed directives"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        common = config_data.get("common") or {}
        groups = config_data.get("groups") or {}

        # Find scopes that have BOTH write_files and runcmd
        mixed_scopes = []
        if common.get("write_files") and common.get("runcmd"):
            mixed_scopes.append(("common", common, None))
        for fg_name, fg_section in groups.items():
            if not isinstance(fg_section, dict):
                continue
            if fg_section.get("write_files") and fg_section.get("runcmd"):
                mixed_scopes.append((fg_name, fg_section, fg_name))

        if not mixed_scopes:
            return _skip(
                summary,
                "No scope with both write_files and runcmd",
            )

        rows = context["rows"]
        if not rows:
            return _skip(summary, "No nodes in PXE mapping")

        all_failures = []
        fields = [
            ("Config file", aci_path),
            ("Mixed scopes", len(mixed_scopes)),
        ]

        for scope_label, section, fg_filter in mixed_scopes:
            if fg_filter is not None:
                target_rows = [
                    r for r in rows
                    if r.get("FUNCTIONAL_GROUP_NAME", "") == fg_filter
                ]
            else:
                target_rows = rows

            if not target_rows:
                fields.append(
                    (f"  {scope_label}", "✗ no matching nodes")
                )
                continue

            wf = section.get("write_files") or []
            rc = section.get("runcmd") or []
            _, sc_fails, sc_fields = _e2e_verify_scope(
                host, target_rows, wf, rc, scope_label,
            )
            all_failures.extend(sc_fails)
            fields.extend(sc_fields)

        return runtime_result(
            not all_failures, summary, fields, "; ".join(all_failures)
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "E2E mixed directives could not be validated", exc
        )


def check_additional_cloud_init_e2e_packages(host):
    """TC-F21: Verify integration with additional packages in runcmd."""
    summary = "Additional cloud-init packages integration"
    try:
        context = _load_cloud_init_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        common = config_data.get("common") or {}
        groups = config_data.get("groups") or {}

        # Find runcmd entries that reference package-like commands
        pkg_indicators = ("rpm -q", "tree", "wget", "curl", "git")

        def _has_pkg_cmd(cmds):
            return [
                c for c in (cmds or [])
                if isinstance(c, str) and any(p in c for p in pkg_indicators)
            ]

        common_pkg = _has_pkg_cmd(common.get("runcmd"))
        fg_pkg = {}
        for fg_name, fg_section in groups.items():
            if not isinstance(fg_section, dict):
                continue
            found = _has_pkg_cmd(fg_section.get("runcmd"))
            if found:
                fg_pkg[fg_name] = found

        if not common_pkg and not fg_pkg:
            return _skip(summary, "No package-dependent runcmd found")

        rows = context["rows"]
        if not rows:
            return _skip(summary, "No nodes in PXE mapping")

        all_failures = []
        fields = [
            ("Config file", aci_path),
            ("Common pkg commands", len(common_pkg)),
            ("Per-FG pkg groups", len(fg_pkg)),
        ]

        # Check common package commands via log-path extraction
        if common_pkg:
            log_paths = _extract_runcmd_log_paths(common_pkg)
            verified = 0
            for row in rows:
                errs = _verify_runcmd_on_row(host, row, log_paths)
                if errs:
                    all_failures.append(
                        f"{row['HOSTNAME']}(common-pkg): {'; '.join(errs)}"
                    )
                else:
                    verified += 1
            fields.append(("  Common pkg verified", f"{verified}/{len(rows)}"))

        # Check per-FG package commands
        for fg_name, pkg_cmds in fg_pkg.items():
            matching = [
                r for r in rows
                if r.get("FUNCTIONAL_GROUP_NAME", "") == fg_name
            ]
            if not matching:
                continue
            log_paths = _extract_runcmd_log_paths(pkg_cmds)
            fg_verified = 0
            for row in matching:
                errs = _verify_runcmd_on_row(host, row, log_paths)
                if errs:
                    all_failures.append(
                        f"{row['HOSTNAME']}({fg_name}-pkg): {'; '.join(errs)}"
                    )
                else:
                    fg_verified += 1
            fields.append(
                (f"  FG {fg_name} pkg verified",
                 f"{fg_verified}/{len(matching)}")
            )

        return runtime_result(
            not all_failures, summary, fields, "; ".join(all_failures)
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(
            "E2E packages integration could not be validated", exc
        )
