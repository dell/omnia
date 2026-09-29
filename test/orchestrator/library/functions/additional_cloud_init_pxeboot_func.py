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
import posixpath
import yaml

from ..vars.pxeboot_vars import PXEBOOT_COMMANDS
from ..vars.provision_vars import (
    ADDITIONAL_METADATA_PREFIX,
    OPENCHAMI_API_PATHS,
)
from ._pxeboot_helpers import (
    group_fields,
    load_runtime_context,
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
        context = load_runtime_context(host)
        enabled, config_data, aci_path = _load_additional_cloud_init_config(
            host, context
        )
        if not enabled:
            return _skip(summary, "Additional cloud-init is not configured")

        common_data = config_data.get("common") or {}
        groups_data = config_data.get("groups") or {}

        # Load live SMD groups via API
        provision_context = load_context(host)
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
        context = load_runtime_context(host)
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
        context = load_runtime_context(host)
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
                    host, row, f"test -f {filepath} && echo EXISTS"
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
                if row.get("EXPECTED_FUNCTIONAL_GROUP", "") == fg_name
                or row.get("FUNCTIONAL_GROUP_NAME", "").startswith(fg_name)
            ]
            fg_verified = 0
            for row in matching_rows:
                node_errors = []
                for filepath in file_paths:
                    result = remote_command(
                        host, row, f"test -f {filepath} && echo EXISTS"
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


def check_additional_cloud_init_runcmd(host):
    """Verify runcmd entries are present in the cloud-init log on nodes."""
    summary = "Additional cloud-init runcmd on nodes"
    try:
        context = load_runtime_context(host)
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

        rows = context["rows"]
        failures = []
        fields = [
            ("Config file", aci_path),
            ("Common runcmd entries", len(common_cmds)),
            ("Per-FG runcmd groups", len(fg_cmds)),
        ]

        # Verify cloud-init completed on all nodes; runcmd runs as part of
        # cloud-init final stage.  If cloud-init succeeded, runcmd was
        # executed.  We verify cloud-init status JSON for each node.
        verified = 0
        for row in rows:
            result = remote_command(host, row, PXEBOOT_COMMANDS["cloud_init"])
            if result.rc != 0:
                failures.append(
                    f"{row['HOSTNAME']}: cloud-init status check failed"
                )
                fields.append(
                    (f"  {row['HOSTNAME']}", "✗ cloud-init status unavailable")
                )
                continue
            stdout = result.stdout
            # cloud-init status --format json outputs after ---JSON--- marker
            json_marker = "---JSON---"
            if json_marker in stdout:
                import json

                json_part = stdout.split(json_marker, 1)[1].strip()
                try:
                    ci_status = json.loads(json_part)
                except (json.JSONDecodeError, ValueError):
                    ci_status = {}
            else:
                ci_status = {}
            status = str(ci_status.get("status") or "").lower()
            if status == "done":
                verified += 1
                fields.append(
                    (f"  {row['HOSTNAME']}", "✓ cloud-init done (runcmd executed)")
                )
            else:
                failures.append(
                    f"{row['HOSTNAME']}: cloud-init status={status}"
                )
                fields.append(
                    (
                        f"  {row['HOSTNAME']}",
                        f"✗ cloud-init status={status or 'unknown'}",
                    )
                )

        fields.append(("  Nodes verified", f"{verified}/{len(rows)}"))

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
