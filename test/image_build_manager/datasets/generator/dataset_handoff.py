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
"""Create the manifest and customer handoff for a generated dataset."""

import shlex
from pathlib import Path
from typing import Any, Callable

from .dataset_publication import sha256_file
from .dataset_rendering import DOCUMENT_ORDER, DOCUMENT_OUTPUTS


def external_inputs(
    repo_variant: str, documents: dict[str, dict[str, Any]]
) -> list[str]:
    """Describe inputs that must exist outside the generated dataset."""
    inputs = [
        "Encrypted domain credential pair configured on the execution OIM"
    ]
    config = documents["image_build_config"]
    if config.get("functional_groups_source") == "catalog":
        inputs.append("CATALOG_FILE_PATH on the execution target")
    if repo_variant == "offline":
        inputs.append(
            "Reachable Repo Manager endpoints and its TLS certificate on the target"
        )
    else:
        inputs.append("Outbound internet access from the image-builder environment")
    return inputs


def artifact_hashes(output_dir: Path, generated: list[str]) -> dict[str, str]:
    """Collect deterministic hashes for generated YAML artifacts."""
    return {
        relative_path: sha256_file(output_dir / relative_path)
        for relative_path in sorted(generated)
    }


def replacement_marker_count(output_dir: Path, generated: list[str]) -> int:
    """Count actionable replacement markers in generated YAML documents."""
    count = 0
    for relative_path in generated:
        if relative_path.endswith((".yml", ".yaml")):
            content = (output_dir / relative_path).read_text(encoding="utf-8")
            count += content.count("REPLACE WITH REAL VALUE")
    return count


def write_manifest(
    output_dir: Path,
    artifacts: dict[str, str],
    plan: dict[str, Any],
    generator_version: int,
    yaml_serializer: Callable[[dict[str, Any]], str],
) -> str:
    """Write deterministic dataset provenance and content hashes."""
    manifest = {
        "schema_version": 2,
        "generator_version": generator_version,
        "dataset": plan["dataset"],
        "profile": plan["profile"],
        "mode": plan["mode"],
        "repo_variant": plan["repo_variant"],
        "repo_host": plan.get("repo_host"),
        "replacement_marker_count": plan["replacement_marker_count"],
        "source_documents": plan["provenance"],
        "normalizations": plan["normalizations"],
        "patches": plan["patches"],
        "replacements": plan["replacements"],
        "customer_guidance": {
            document_name: instructions["checklist"]
            for document_name, instructions in plan["guidance"].items()
        },
        "external_inputs": plan["external_inputs"],
        "artifacts": artifacts,
    }
    manifest_name = "dataset_manifest.yml"
    (output_dir / manifest_name).write_text(
        "---\n" + yaml_serializer(manifest), encoding="utf-8"
    )
    return manifest_name


def regeneration_command(plan: dict[str, Any]) -> str:
    """Build a shell-safe command that preserves the selected CLI overrides."""
    command = ["./generate_dataset.py", "create", plan["dataset"]]
    if plan["mode"] == "from-src":
        command.extend(["--from-src", "--repo-variant", plan["repo_variant"]])
    else:
        command.extend(["--profile", plan["profile"]])
        command.extend(["--repo-variant", plan["repo_variant"]])
        for assignment in plan["set_values"]:
            command.extend(["--set", assignment])
        for assignment in plan["legacy_values"]:
            command.extend(["--var", assignment])
    if plan.get("repo_host"):
        command.extend(["--repo-host", plan["repo_host"]])
    command.append("--force")
    return shlex.join(command)


def write_readme(
    output_dir: Path,
    plan: dict[str, Any],
    generated: list[str],
    regenerate: str,
) -> str:
    """Write a deterministic, customer-facing dataset handoff."""
    readme_name = "README.md"
    files = sorted([*generated, readme_name])
    lines = [
        f"# Dataset: {plan['dataset']}",
        "",
        "Generated from canonical `src/image_build_manager` examples by",
        "`datasets/generator/generate_dataset.py`.",
        "",
        f"- Profile: `{plan['profile']}`",
        f"- Mode: `{plan['mode']}`",
        f"- Repository variant: `{plan['repo_variant']}`",
        f"- Required value replacements: `{plan['replacement_marker_count']}`",
        "- Provenance and source hashes: `dataset_manifest.yml`",
        "",
        "## Files",
        "",
        *(f"- `{relative_path}`" for relative_path in files),
        "",
    ]
    if plan["normalizations"]:
        lines.extend(
            [
                "## Source normalizations",
                "",
                *(f"- {item}" for item in plan["normalizations"]),
                "",
            ]
        )
    lines.extend(
        [
            "## External inputs",
            "",
            *(f"- {item}" for item in plan["external_inputs"]),
            "",
            "## Customer edit checklist",
            "",
        ]
    )
    _append_document_checklists(lines, plan)
    lines.extend(_usage_sections(plan, regenerate))
    (output_dir / readme_name).write_text("\n".join(lines), encoding="utf-8")
    return readme_name


def _append_document_checklists(
    lines: list[str], plan: dict[str, Any]
) -> None:
    """Append each document's shared customer checklist."""
    for document_name in DOCUMENT_ORDER:
        output_name = DOCUMENT_OUTPUTS[document_name]
        lines.extend(
            [
                f"### `{output_name}`",
                "",
                *(
                    f"- {item}"
                    for item in plan["guidance"][document_name]["checklist"]
                ),
                "",
            ]
        )


def _usage_sections(plan: dict[str, Any], regenerate: str) -> list[str]:
    """Return credential, review, regeneration, and execution instructions."""
    dataset = plan["dataset"]
    return [
        "Credentials are never generated in or copied from a dataset, and the",
        "framework never syncs domain credentials. On the execution OIM, from",
        "`test/image_build_manager`, run `./setup_env.sh --set-domain-creds`.",
        "`test_creds.yml` remains SSH-only.",
        "",
        "From `test/image_build_manager`, find every required value replacement:",
        "",
        "```bash",
        "grep -R -n 'REPLACE WITH REAL VALUE' \\",
        f"  datasets/{dataset}/input/ datasets/{dataset}/repo_manager_output/",
        "```",
        "",
        "## Regenerate",
        "",
        "From `test/image_build_manager`:",
        "",
        "```bash",
        "cd datasets/generator/",
        regenerate,
        "```",
        "",
        "## Use",
        "",
        f"Set `dataset: \"{dataset}\"` in `test_config.yml`. On a clean target,",
        "enable both `sync_image_build_input` and `sync_output` so only this",
        "dataset's non-secret input files and `repo_status.yml` are copied. On a",
        "prepared target, enable only the sync operations needed for that",
        "environment.",
        "",
    ]
