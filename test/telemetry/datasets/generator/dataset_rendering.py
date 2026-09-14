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
"""Customer-safe values and guidance for generated telemetry dataset YAML."""

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
from ruamel.yaml.error import YAMLError as RuamelYAMLError


DOCUMENT_TITLES = {
    "telemetry_config": "Telemetry configuration",
    "telemetry_storage_config": "Telemetry storage resource configuration",
    "telemetry_packages": "Telemetry packages and install mode",
}

DOCUMENT_OUTPUTS = {
    "telemetry_config": "input/telemetry_config.yml",
    "telemetry_storage_config": "input/telemetry_storage_config.yml",
    "telemetry_packages": "input/telemetry_packages.yml",
}

DOCUMENT_ORDER = (
    "telemetry_config",
    "telemetry_storage_config",
    "telemetry_packages",
)

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_DOCUMENT_TEMPLATE = "document.yml.j2"

# Guidance notes
_CLUSTER_INVENTORY_NOTE = "REPLACE WITH REAL VALUE: path to your orchestrator inventory"
_BMC_DATA_PATH_NOTE = "REPLACE WITH REAL VALUE: path to BMC group CSV when iDRAC is enabled"
_UFM_ENDPOINT_NOTE = "REPLACE WITH REAL VALUE when UFM is enabled"
_VAST_ENDPOINT_NOTE = "REPLACE WITH REAL VALUE when VAST is enabled"
_CSM_VALUES_NOTE = "REPLACE WITH REAL VALUE when PowerScale is enabled"
_INSTALL_MODE_NOTE = "Set to 'online' for internet access or 'offline' for air-gapped"
_REPO_URL_NOTE = "REPLACE WITH REAL VALUE: Pulp repository URL when install_mode is offline"
_MOUNT_NOTE = "VERIFY this mount path matches your cluster configuration"

_SENSITIVE_PARTS = {
    "password", "secret", "token", "credential", "access_key",
}


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
    """Render every dataset YAML document through the shared template."""
    environment = _template_environment()
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
        except (TemplateError, RuamelYAMLError, UnicodeError) as exc:
            raise DatasetRenderingError(
                f"Template render failed for {_DOCUMENT_TEMPLATE}: {exc}"
            ) from exc
        output_path = output_dir / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        generated.append(output_name)
    return generated


def prepare_customer_documents(
    documents: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Return safe concrete YAML values derived from the source examples."""
    return copy.deepcopy(documents)


def document_normalizations() -> list[str]:
    """Describe intentional source-to-dataset safety transformations."""
    return []


def is_sensitive_target(target: str) -> bool:
    """Return whether a CLI target appears to contain credential material."""
    normalized = target.lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_PARTS)


def document_guidance(
    documents: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build the edit instructions shared by YAML, manifest, and README."""
    config = documents["telemetry_config"]
    sources = config.get("telemetry_sources", {})

    # --- telemetry_config guidance ---
    config_notes = [
        "REVIEW BEFORE USE: cluster_inventory must point to the orchestrator inventory on the target.",
    ]
    idrac = sources.get("idrac", {})
    if idrac.get("metrics_enabled", False):
        config_notes.append(
            "REVIEW BEFORE USE: idrac_telemetry_configurations.bmc_group_data_path "
            "must point to a valid BMC CSV file."
        )
    ufm = sources.get("ufm", {})
    if ufm.get("metrics_enabled", False):
        config_notes.append(
            "REPLACE BEFORE USE: ufm_configuration.ufm_endpoint must be set "
            "to the reachable UFM appliance IP."
        )
    vast = sources.get("vast", {})
    if vast.get("metrics_enabled", False):
        config_notes.append(
            "REPLACE BEFORE USE: vast_configuration.vast_endpoint must be set "
            "to the reachable VAST cluster IP."
        )
    ps = sources.get("powerscale", {})
    if ps.get("metrics_enabled", False):
        config_notes.append(
            "REPLACE BEFORE USE: powerscale_configurations.csm_observability_values_file_path "
            "must point to the Karavi values.yaml file."
        )

    # --- telemetry_storage_config guidance ---
    storage_notes = [
        "OPTIONAL: adjust resource requests and limits for your cluster capacity.",
        "NO REPLACEMENT REQUIRED: defaults are suitable for most deployments.",
    ]

    # --- telemetry_packages guidance ---
    packages = documents["telemetry_packages"]
    install_mode = packages.get("install_mode", "offline")
    if install_mode == "offline":
        packages_notes = [
            "REVIEW BEFORE USE: install_mode is 'offline'; verify repo_url points to your Pulp repository.",
            "REVIEW BEFORE USE: verify k8s_cluster_mount and slurm_cluster_mount paths.",
        ]
    else:
        packages_notes = [
            "NO REPLACEMENT REQUIRED: install_mode is 'online'; images pulled from public registries.",
            "REVIEW BEFORE USE: verify k8s_cluster_mount and slurm_cluster_mount paths.",
        ]

    return {
        "telemetry_config": {"checklist": config_notes, "field_notes": {}},
        "telemetry_storage_config": {"checklist": storage_notes, "field_notes": {}},
        "telemetry_packages": {"checklist": packages_notes, "field_notes": {}},
    }
