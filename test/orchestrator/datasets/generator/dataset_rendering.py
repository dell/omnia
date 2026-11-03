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
"""Jinja2 rendering for Orchestrator dataset YAML documents."""

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

_DOCUMENT_TITLES = {
    "additional_cloud_init": "Additional cloud-init configuration",
    "high_availability_config": "High availability configuration",
    "network_spec": "Network specification",
    "omnia_config": "Omnia configuration",
    "orchestrator_config": "Orchestrator configuration",
    "pxe_mapping_file": "PXE mapping file",
    "security_config": "Security configuration",
    "set_pxe_boot_config": "PXE boot configuration",
    "storage_config": "Storage configuration",
}

_DOCUMENT_OUTPUTS = {
    "additional_cloud_init": "input/additional_cloud_init.yml",
    "high_availability_config": "input/high_availability_config.yml",
    "network_spec": "input/network_spec.yml",
    "omnia_config": "input/omnia_config.yml",
    "orchestrator_config": "input/orchestrator_config.yml",
    "pxe_mapping_file": "input/pxe_mapping_file.csv",
    "security_config": "input/security_config.yml",
    "set_pxe_boot_config": "input/set_pxe_boot_config.yml",
    "storage_config": "input/storage_config.yml",
}

_DOCUMENT_ORDER = (
    "additional_cloud_init",
    "high_availability_config",
    "network_spec",
    "omnia_config",
    "orchestrator_config",
    "pxe_mapping_file",
    "security_config",
    "set_pxe_boot_config",
    "storage_config",
)

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_DOCUMENT_TEMPLATE = "document.yml.j2"


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
    output_dir: Path,
) -> list[str]:
    """Render every dataset YAML document through the one shared template."""
    environment = _template_environment()
    generated: list[str] = []
    for document_name in _DOCUMENT_ORDER:
        if document_name not in documents:
            continue
        output_name = _DOCUMENT_OUTPUTS[document_name]
        try:
            content = environment.get_template(_DOCUMENT_TEMPLATE).render(
                document=documents[document_name],
                guidance=guidance[document_name]["checklist"],
                source=provenance[document_name]["path"],
                title=_DOCUMENT_TITLES[document_name],
            )
        except (TemplateError, UnicodeError) as exc:
            raise DatasetRenderingError(
                f"Template render failed for {_DOCUMENT_TEMPLATE}: {exc}"
            ) from exc
        output_path = output_dir / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        generated.append(output_name)
    return generated


def document_guidance(
    documents: dict[str, dict[str, Any]], profile_name: str
) -> dict[str, dict[str, Any]]:
    """Build the edit instructions shared by YAML, manifest, and README."""
    checklists = {}
    for document_name in _DOCUMENT_ORDER:
        if document_name not in documents:
            continue
        notes = [
            "REVIEW BEFORE USE: verify this configuration matches your target environment.",
            f"Dataset profile: {profile_name}",
        ]
        checklists[document_name] = {
            "checklist": notes,
            "field_notes": {},
        }
    return checklists
