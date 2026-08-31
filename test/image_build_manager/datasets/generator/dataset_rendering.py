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
"""Customer-safe values and guidance for generated dataset YAML."""

import copy
from io import StringIO
from pathlib import Path
from typing import Any

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateError,
    select_autoescape,
)
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.error import YAMLError as RuamelYAMLError

from .dataset_network import DOCUMENTATION_REPO_MANAGER_HOST


DOCUMENT_TITLES = {
    "image_build_config": "Image Build Manager configuration",
    "package_groups": "Config-mode package groups",
    "repo_status": "Repo Manager output contract",
}

DOCUMENT_OUTPUTS = {
    "image_build_config": "input/image_build_config.yml",
    "package_groups": "input/package_groups.yml",
    "repo_status": "repo_manager_output/repo_status.yml",
}

DOCUMENT_ORDER = (
    "image_build_config",
    "package_groups",
    "repo_status",
)

_SOURCE_ADMIN_IP_TOKEN = "{{ admin_nic_ip }}"
_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_DOCUMENT_TEMPLATE = "document.yml.j2"

_REPO_PATH_NOTE = (
    "Change only if the runtime project or Repo Manager output path differs."
)
_MINIO_ENDPOINT_NOTE = "LEAVE EMPTY for MinIO; its endpoint is discovered at runtime."
_POWERSCALE_ENDPOINT_NOTE = "VERIFY this is the reachable PowerScale S3 URL."
_ARM_IP_EMPTY_NOTE = "OPTIONAL: leave empty to skip ARM image builds."
_ARM_IP_SET_NOTE = "VERIFY this identifies the ARM build host."
_ARM_USER_UNUSED_NOTE = "IGNORED while the ARM build-host IP is empty."
_ARM_USER_SET_NOTE = "VERIFY this account can connect to the ARM build host."
_OS_VERSION_NOTE = "Keep consistent with repo_status.yml repository versions."
_REPO_URL_NOTE = "REPLACE WITH REAL VALUE: use a reachable Repo Manager URL."
_PRODUCER_ONLY_URL_NOTE = (
    "REFERENCE ONLY: producer field; ignored by Image Build Manager."
)
_OFFLINE_CERT_NOTE = "VERIFY this Repo Manager certificate exists on the target."
_INTERNET_CERT_NOTE = "LEAVE EMPTY: public repositories use the system trust store."
_SLURM_REPO_NOTE = (
    "Keep empty unless the selected catalog or package groups require Slurm packages."
)


class DatasetRenderingError(Exception):
    """Raised when a dataset document cannot be rendered safely."""


def serialize_yaml(document: dict[str, Any]) -> str:
    """Serialize deterministically while retaining source and inline comments."""
    writer = YAML(typ="rt")
    writer.preserve_quotes = True
    writer.default_flow_style = False
    writer.explicit_start = False
    writer.width = 120
    writer.indent(mapping=2, sequence=4, offset=2)
    stream = StringIO()
    writer.dump(document, stream)
    return stream.getvalue()


def _template_environment() -> Environment:
    """Create the strict Jinja environment shared by every YAML document."""
    environment = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=StrictUndefined,
        autoescape=select_autoescape(default_for_string=False, default=False),
        keep_trailing_newline=True,
    )
    environment.filters["to_yaml"] = serialize_yaml
    return environment


def render_documents(
    documents: dict[str, dict[str, Any]],
    provenance: dict[str, dict[str, str]],
    guidance: dict[str, dict[str, Any]],
    repo_variant: str,
    output_dir: Path,
) -> list[str]:
    """Render every dataset YAML document through the one shared template."""
    environment = _template_environment()
    package_source = str(
        documents["image_build_config"].get("functional_groups_source", "config")
    )
    generated: list[str] = []
    for document_name in DOCUMENT_ORDER:
        output_name = DOCUMENT_OUTPUTS[document_name]
        try:
            content = environment.get_template(_DOCUMENT_TEMPLATE).render(
                document=documents[document_name],
                guidance=guidance[document_name]["checklist"],
                source=provenance[document_name]["path"],
                title=DOCUMENT_TITLES[document_name],
            )
            content = annotate_rendered_yaml(
                document_name,
                content,
                repo_variant,
                package_source,
                guidance[document_name],
            )
        except (TemplateError, RuamelYAMLError, UnicodeError) as exc:
            raise DatasetRenderingError(
                f"Template render failed for {_DOCUMENT_TEMPLATE}: {exc}"
            ) from exc
        output_path = output_dir / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        generated.append(output_name)
    return generated


def _replace_text(value: Any, old: str, new: str) -> Any:
    """Recursively replace one source-example token while preserving comments."""
    if isinstance(value, dict):
        for key, nested_value in value.items():
            value[key] = _replace_text(nested_value, old, new)
        return value
    if isinstance(value, list):
        for index, item in enumerate(value):
            value[index] = _replace_text(item, old, new)
        return value
    if isinstance(value, str):
        return value.replace(old, new)
    return value


def prepare_customer_documents(
    documents: dict[str, dict[str, Any]], repo_variant: str
) -> dict[str, dict[str, Any]]:
    """Return safe concrete YAML values derived from the source examples.

    The offline source sample intentionally contains an Ansible/Jinja token.
    A generated YAML dataset is not rendered by Ansible, so emitting that token
    would create an unusable repository URL. Replace it with a reserved
    ``.invalid`` documentation hostname that is visibly non-production.
    """
    prepared = copy.deepcopy(documents)
    if repo_variant != "offline":
        return prepared

    repo_status = _replace_text(
        prepared["repo_status"],
        _SOURCE_ADMIN_IP_TOKEN,
        DOCUMENTATION_REPO_MANAGER_HOST,
    )
    # Image Build Manager does not consume registries. The source sample still
    # carries a legacy shape that differs from current Repo Manager output, so
    # do not expose stale fake registry settings in a customer dataset.
    if "registries" in repo_status:
        repo_status["registries"] = CommentedMap()
    prepared["repo_status"] = repo_status
    return prepared


def replace_documentation_repo_host(
    documents: dict[str, dict[str, Any]], host: str
) -> None:
    """Replace the one offline dummy host consistently in every output URL."""
    documents["repo_status"] = _replace_text(
        documents["repo_status"], DOCUMENTATION_REPO_MANAGER_HOST, host
    )


def document_normalizations(
    repo_variant: str, repo_host: str | None = None
) -> list[str]:
    """Describe intentional source-to-dataset safety transformations."""
    normalizations: list[str] = []
    if repo_variant == "offline":
        host_summary = (
            f"Resolved literal {{{{ admin_nic_ip }}}} URL tokens to {repo_host}."
            if repo_host
            else "Replaced literal {{ admin_nic_ip }} URL tokens with the reserved "
            f"dummy host {DOCUMENTATION_REPO_MANAGER_HOST}."
        )
        normalizations.extend(
            [
                host_summary,
                "Cleared the legacy registry example because Image Build Manager "
                "does not consume registry metadata.",
            ]
        )
    return normalizations


def _contains_text(value: Any, needle: str) -> bool:
    """Return whether a scalar anywhere below value contains needle."""
    if isinstance(value, dict):
        return any(_contains_text(item, needle) for item in value.values())
    if isinstance(value, list):
        return any(_contains_text(item, needle) for item in value)
    return isinstance(value, str) and needle in value


def document_guidance(
    documents: dict[str, dict[str, Any]], repo_variant: str
) -> dict[str, dict[str, Any]]:
    """Build the edit instructions shared by YAML, manifest, and README."""
    config = documents["image_build_config"]
    package_source = config.get("functional_groups_source", "config")
    s3_value = config.get("s3_configurations", {})
    s3_config = s3_value if isinstance(s3_value, dict) else {}

    config_notes = [
        "REVIEW BEFORE USE: repo_manager_output_path must point to repo_status.yml on the target.",
    ]
    if s3_config.get("provider") == "powerscale":
        config_notes.append(
            "VERIFY BEFORE USE: s3_configurations.endpoint_url must be the "
            "reachable PowerScale S3 URL."
        )
    else:
        config_notes.append(
            "NO REPLACEMENT REQUIRED: MinIO endpoint_url stays empty and "
            "is discovered at runtime."
        )
    if config.get("aarch64_inventory_host_ip"):
        config_notes.append(
            "REVIEW BEFORE USE: aarch64_inventory_host_ip and "
            "aarch64_ssh_user must identify the ARM host."
        )
    else:
        config_notes.append(
            "OPTIONAL: leave aarch64_inventory_host_ip empty to skip ARM image builds."
        )

    package_notes = (
        [
            "REVIEW BEFORE USE: verify os, os_version, base_packages, and "
            "functional_groups for the target.",
            "OPTIONAL: customize package values only when the target package "
            "selection differs from this source example.",
        ]
        if package_source == "config"
        else [
            "NO REPLACEMENT REQUIRED: catalog mode ignores this file and "
            "reads CATALOG_FILE_PATH instead.",
        ]
    )

    repo_notes: list[str]
    if repo_variant == "offline":
        repo_notes = [
            "REVIEW BEFORE USE: this file simulates repo_status.yml produced by Repo Manager.",
        ]
        repo_status = documents["repo_status"]
        if _contains_text(repo_status, DOCUMENTATION_REPO_MANAGER_HOST):
            repo_notes.append(
                "REQUIRED BEFORE USE: replace the dummy host in every active "
                "repositories URL, preferably with --repo-host."
            )
            repo_notes.append(
                "REFERENCE ONLY: file_repos and legacy top-level URL fields are "
                "retained for producer fidelity but ignored by Image Build Manager."
            )
        repo_notes.append(
            "REVIEW BEFORE USE: repo_manager.certificates paths must exist on the execution target."
        )
    else:
        repo_notes = [
            "NO REPLACEMENT REQUIRED: the listed CentOS Stream and EPEL URLs "
            "are intentional public test repos.",
            "OPTIONAL: use approved internal mirrors instead when policy "
            "requires them.",
        ]

    checklists = {
        "image_build_config": config_notes,
        "package_groups": package_notes,
        "repo_status": repo_notes,
    }
    return {
        document_name: {
            "checklist": checklist,
            "field_notes": _field_notes(document_name, documents, repo_variant),
            "dummy_url_note": (
                _REPO_URL_NOTE
                if document_name == "repo_status" and repo_variant == "offline"
                else ""
            ),
        }
        for document_name, checklist in checklists.items()
    }


def _normalize_source_comments(
    document_name: str,
    content: str,
    repo_variant: str,
    package_source: str,
) -> str:
    """Correct known source-example comments for the effective dataset mode."""
    if document_name == "image_build_config":
        content = content.replace(
            "# Edit this file, then run: ./domain-init.sh  (or omnia.sh --init)",
            "# Select this dataset in test_config.yml and enable the required sync flags.",
        )
        content = content.replace(
            "#   boot-images  — OS boot images (kernel, initramfs, rootfs)\n"
            "#   efi-images   — EFI boot artifacts",
            "#   boot-images  — OS images; EFI objects use its efi-images/ prefix\n"
            "#   efi          — auxiliary EFI bucket created during preparation",
        )
    if document_name == "package_groups":
        content = content.replace(
            "# This file is a template shipped in the source tree under input/.\n"
            "# domain-init.sh copies it to the runtime project directory:\n"
            "#   <OMNIA_DATA_PATH>/image_build_manager/input/<project>/package_groups.yml",
            "# This generated file is a dataset input source. When input sync is\n"
            "# enabled, the test framework copies it to the target project directory.",
        )
        content = content.replace(
            "# See image_build_config.yml Section 5.",
            "# See image_build_config.yml Section 4.",
        )
        content = content.replace(
            "# Each key is a functional group name (must match image_build_config.yml entries).",
            "# Each key is a functional group name with a supported architecture suffix.",
        )
    if document_name == "repo_status" and repo_variant == "offline":
        content = content.replace(
            "# image_build_manager pre-check validates:",
            "# Required consumer contract:",
        )
        content = content.replace(
            "#   3. rpm_repos contains valid URLs for the target architectures",
            "#   3. repositories contains valid URLs for the target architectures",
        )
        content = content.replace(
            "#   1. Copy this file to the runtime location:\n"
            "#      mkdir -p /opt/omnia/repo_manager/output/project_default\n"
            "#      cp repo_status.yml /opt/omnia/repo_manager/output/project_default/",
            "#   1. Select this dataset in test_config.yml and enable sync_output.",
        )
        content = content.replace(
            "#   3. Verify: omnia-cli repo-manager",
            "#   3. Run Image Build Manager validation after dataset synchronization.",
        )
    if document_name == "repo_status" and repo_variant == "internet":
        content = content.replace(
            "#   1. Copy this file to the runtime location:\n"
            "#      mkdir -p /opt/omnia/repo_manager/output/project_default\n"
            "#      cp repo_status_internet.yml \\\n"
            "#         /opt/omnia/repo_manager/output/project_default/repo_status.yml",
            "#   1. Select this dataset in test_config.yml and enable sync_output.",
        )
    if (
        document_name == "repo_status"
        and repo_variant == "internet"
        and package_source == "config"
    ):
        content = content.replace(
            "#   3. Set functional_groups_source to 'catalog' in image_build_config.yml\n"
            "#      and set CATALOG_FILE_PATH in omnia.env to your test catalog JSON.",
            "#   3. This dataset uses functional_groups_source: config. Packages come\n"
            "#      from input/package_groups.yml; CATALOG_FILE_PATH is not required.",
        )
    return content


def _field_notes(
    document_name: str,
    documents: dict[str, dict[str, Any]],
    repo_variant: str,
) -> dict[str, str]:
    """Return notes that reflect the rendered values and selected mode."""
    config = documents["image_build_config"]
    s3_value = config.get("s3_configurations", {})
    s3_config = s3_value if isinstance(s3_value, dict) else {}
    arm_enabled = bool(str(config.get("aarch64_inventory_host_ip", "")).strip())
    endpoint_note = (
        _POWERSCALE_ENDPOINT_NOTE
        if s3_config.get("provider") == "powerscale"
        else _MINIO_ENDPOINT_NOTE
    )
    return {
        "image_build_config": {
            "repo_manager_output_path": _REPO_PATH_NOTE,
            "endpoint_url": endpoint_note,
            "aarch64_inventory_host_ip": (
                _ARM_IP_SET_NOTE if arm_enabled else _ARM_IP_EMPTY_NOTE
            ),
            "aarch64_ssh_user": (
                _ARM_USER_SET_NOTE if arm_enabled else _ARM_USER_UNUSED_NOTE
            ),
        },
        "package_groups": {"os_version": _OS_VERSION_NOTE},
        "repo_status": {
            "server_crt": (
                _OFFLINE_CERT_NOTE
                if repo_variant == "offline"
                else _INTERNET_CERT_NOTE
            )
        },
    }[document_name]


def annotate_rendered_yaml(
    document_name: str,
    content: str,
    repo_variant: str,
    package_source: str,
    instructions: dict[str, Any],
) -> str:
    """Add value-aware markers without disturbing source guidance."""
    content = _normalize_source_comments(
        document_name, content, repo_variant, package_source
    )
    notes = instructions["field_notes"]
    dummy_url_note = instructions["dummy_url_note"]
    rendered_lines: list[str] = []
    in_repositories = False
    for line in content.splitlines():
        line = line.replace(" # noqa: yaml[line-length]", "").rstrip()
        stripped = line.lstrip()
        comment = ""
        if stripped and not stripped.startswith("#") and ":" in stripped:
            key = stripped.split(":", 1)[0].strip("'\"")
            if len(line) == len(stripped):
                in_repositories = key == "repositories"
            comment = notes.get(key, "")
            if (
                document_name == "repo_status"
                and repo_variant == "offline"
                and DOCUMENTATION_REPO_MANAGER_HOST in line
            ):
                comment = (
                    dummy_url_note
                    if in_repositories
                    else _PRODUCER_ONLY_URL_NOTE
                )
            elif (
                document_name == "repo_status"
                and repo_variant == "internet"
                and key == "slurm_custom"
            ):
                comment = _SLURM_REPO_NOTE
        if comment and comment not in line:
            line = f"{line}  # {comment}"
        rendered_lines.append(line)
    return "\n".join(rendered_lines) + "\n"
