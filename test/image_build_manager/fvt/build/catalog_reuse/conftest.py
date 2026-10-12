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
"""State-safe helpers for the catalog reuse end-to-end suite."""

from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
import os
import posixpath
import shlex
from typing import Any

import pytest
import yaml

from omnia_auto import read_remote_env, resolve_domain_data_path
from library.functions import run_playbook


DOMAIN = "image_build_manager"
EMPTY_DICTIONARY = {
    "dictionary_version": 1,
    "entries": {},
    "last_updated": "",
}


def _catalog_recovery_directory(data_root: str, project: str) -> str:
    """Return a project-scoped recovery path below the domain data root."""
    recovery_key = hashlib.sha256(
        f"{data_root}\0{project}".encode("utf-8")
    ).hexdigest()[:16]
    return posixpath.join(
        data_root,
        ".test-recovery",
        "catalog-reuse",
        recovery_key,
    )


class CatalogReuseContext:
    """Manage one reversible sequence of live catalog build scenarios."""

    def __init__(self, host) -> None:
        self.host = host
        self.project = read_remote_env(host, "OMNIA_PROJECT_NAME")
        self.data_root = resolve_domain_data_path(
            host,
            DOMAIN,
            "OMNIA_DATA_PATH",
            domain_data_path_var="IMAGE_BUILD_MANAGER_DATA_PATH",
        )
        self.recovery_dir = _catalog_recovery_directory(
            self.data_root,
            self.project,
        )
        self.catalog_path = read_remote_env(host, "CATALOG_FILE_PATH")
        self.config_path = (
            f"{self.data_root}/input/{self.project}/image_build_config.yml"
        )
        self.output_dir = f"{self.data_root}/output/{self.project}"
        self.build_status_path = f"{self.output_dir}/build_status.yml"
        self.dictionary_path = f"{self.output_dir}/image_group_dictionary.json"
        self.dictionary_backup_path = f"{self.dictionary_path}.bak"
        self.created_output_paths: set[str] = set()
        self.backup_paths: list[str] = []
        self.absence_markers: list[str] = []

        # Recover the baseline left by an interrupted earlier suite before
        # taking this run's in-memory snapshots.
        for path in (self.config_path, self.catalog_path):
            self._recover_runtime_state(path)

        self.original_config_text = self.read_text(self.config_path)
        self.original_catalog_text = self.read_text(self.catalog_path)
        self.original_config = yaml.safe_load(self.original_config_text)
        self.original_catalog = json.loads(self.original_catalog_text)
        self.repo_path = self.original_config["repo_manager_output_path"]
        catalog_root = self.original_catalog["catalog"]
        catalog_image_group_id = (
            f"{catalog_root['identifier']}-v{catalog_root['version']}"
        )
        self.catalog_build_status_path = (
            f"{self.output_dir}/{catalog_image_group_id}/build_status.yml"
        )
        for path in (
            self.repo_path,
            self.build_status_path,
            self.catalog_build_status_path,
            self.dictionary_path,
            self.dictionary_backup_path,
        ):
            self._recover_runtime_state(path)
        self.original_repo_text = self.read_text(self.repo_path)
        self.original_repo = yaml.safe_load(self.original_repo_text)
        self.build_status_existed = self.exists(self.build_status_path)
        self.original_build_status_text = (
            self.read_text(self.build_status_path)
            if self.build_status_existed
            else ""
        )
        self.catalog_build_status_existed = self.exists(
            self.catalog_build_status_path
        )
        self.original_catalog_build_status_text = (
            self.read_text(self.catalog_build_status_path)
            if self.catalog_build_status_existed
            else ""
        )
        self.dictionary_existed = self.exists(self.dictionary_path)
        self.original_dictionary_text = (
            self.read_text(self.dictionary_path)
            if self.dictionary_existed
            else ""
        )
        self.dictionary_backup_existed = self.exists(
            self.dictionary_backup_path
        )
        self.original_dictionary_backup_text = (
            self.read_text(self.dictionary_backup_path)
            if self.dictionary_backup_existed
            else ""
        )
        self._create_runtime_backups()

    # -- target file operations ------------------------------------------
    def run_command(self, command: str):
        """Run one command on the configured OIM target."""
        return self.host.run(command)

    def exists(self, path: str) -> bool:
        """Return whether a target path exists."""
        return self.run_command(
            f"test -e {shlex.quote(path)}"
        ).rc == 0

    def read_text(self, path: str) -> str:
        """Read a required target file."""
        result = self.run_command(f"cat -- {shlex.quote(path)}")
        if result.rc != 0:
            raise RuntimeError(f"Unable to read required file: {path}")
        return result.stdout

    def write_text(self, path: str, content: str) -> None:
        """Atomically write non-secret test input on the target."""
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        quoted_path = shlex.quote(path)
        quoted_parent = shlex.quote(os.path.dirname(path))
        temporary = shlex.quote(f"{path}.catalog-reuse.tmp")
        command = (
            f"mkdir -p {quoted_parent} && "
            f"printf %s {encoded} | base64 --decode > {temporary} && "
            f"chmod 0644 {temporary} && mv -f {temporary} {quoted_path}"
        )
        result = self.run_command(command)
        if result.rc != 0:
            raise RuntimeError(f"Unable to write test input: {path}")

    def remove(self, path: str) -> None:
        """Remove one exact target path."""
        result = self.run_command(f"rm -f -- {shlex.quote(path)}")
        if result.rc != 0:
            raise RuntimeError(f"Unable to remove test file: {path}")

    def remove_tree(self, path: str) -> None:
        """Remove one suite-created directory below the project output."""
        normalized = posixpath.normpath(path)
        output_prefix = f"{posixpath.normpath(self.output_dir)}/"
        if not normalized.startswith(output_prefix):
            raise RuntimeError(
                f"Refusing to remove path outside project output: {path}"
            )
        result = self.run_command(f"rm -rf -- {shlex.quote(normalized)}")
        if result.rc != 0:
            raise RuntimeError(f"Unable to remove test directory: {path}")

    def load_dictionary(self) -> dict[str, Any]:
        """Return the live global dictionary."""
        if not self.exists(self.dictionary_path):
            return deepcopy(EMPTY_DICTIONARY)
        return json.loads(self.read_text(self.dictionary_path))

    def save_dictionary(self, document: dict[str, Any]) -> None:
        """Replace the live dictionary with a test document."""
        self.write_text(
            self.dictionary_path,
            json.dumps(document, indent=2, sort_keys=True) + "\n",
        )

    # -- backup and restoration ------------------------------------------
    def _recovery_path(self, path: str, suffix: str) -> str:
        """Return isolated recovery metadata outside product input paths."""
        path_key = hashlib.sha256(path.encode("utf-8")).hexdigest()
        return f"{self.recovery_dir}/{path_key}.{suffix}"

    def _backup_path(self, path: str) -> str:
        return self._recovery_path(path, "backup")

    def _absence_marker_path(self, path: str) -> str:
        return self._recovery_path(path, "absent")

    def _recovery_directories(self) -> tuple[str, str, str]:
        """Return leaf-to-root recovery directories owned by this suite."""
        recovery_parent = posixpath.dirname(self.recovery_dir)
        recovery_root = posixpath.dirname(recovery_parent)
        return self.recovery_dir, recovery_parent, recovery_root

    def _recover_runtime_state(self, path: str) -> None:
        """Recover one baseline file after an interrupted earlier suite."""
        backup = self._backup_path(path)
        absence_marker = self._absence_marker_path(path)
        backup_exists = self.exists(backup)
        marker_exists = self.exists(absence_marker)
        if backup_exists and marker_exists:
            raise RuntimeError(
                f"Conflicting catalog-reuse recovery state for: {path}"
            )
        if backup_exists:
            result = self.run_command(
                f"cp -f -- {shlex.quote(backup)} {shlex.quote(path)}"
            )
            if result.rc != 0:
                raise RuntimeError(f"Unable to recover stale backup: {backup}")
            self.remove(backup)
        elif marker_exists:
            if self.exists(path):
                self.remove(path)
            self.remove(absence_marker)

    def _create_backup(self, path: str) -> None:
        backup = self._backup_path(path)
        recovery_dir, recovery_parent, recovery_root = (
            self._recovery_directories()
        )
        result = self.run_command(
            f"mkdir -p {shlex.quote(recovery_dir)} && "
            f"chmod 0700 {shlex.quote(recovery_root)} "
            f"{shlex.quote(recovery_parent)} "
            f"{shlex.quote(recovery_dir)} && "
            f"cp -f -- {shlex.quote(path)} {shlex.quote(backup)} && "
            f"chmod 0600 {shlex.quote(backup)}"
        )
        if result.rc != 0:
            raise RuntimeError(f"Unable to create runtime backup: {path}")
        self.backup_paths.append(backup)

    def _create_absence_marker(self, path: str) -> None:
        marker = self._absence_marker_path(path)
        recovery_dir, recovery_parent, recovery_root = (
            self._recovery_directories()
        )
        quoted_recovery_dir = shlex.quote(recovery_dir)
        quoted_marker = shlex.quote(marker)
        result = self.run_command(
            f"mkdir -p {quoted_recovery_dir} && "
            f"chmod 0700 {shlex.quote(recovery_root)} "
            f"{shlex.quote(recovery_parent)} {quoted_recovery_dir} && "
            f": > {quoted_marker} && "
            f"chmod 0600 {quoted_marker}"
        )
        if result.rc != 0:
            raise RuntimeError(
                f"Unable to record absent baseline file: {path}"
            )
        self.absence_markers.append(marker)

    def _prune_empty_recovery_directories(self) -> None:
        """Remove the suite recovery tree when it contains no artifacts."""
        for position, directory in enumerate(self._recovery_directories()):
            if not self.exists(directory):
                continue
            result = self.run_command(
                f"rmdir -- {shlex.quote(directory)}"
            )
            if (
                position == 0
                and result.rc != 0
                and self.exists(directory)
            ):
                raise RuntimeError(
                    f"Unable to remove recovery directory: {directory}"
                )

    def _create_runtime_backups(self) -> None:
        states = (
            (self.config_path, True),
            (self.catalog_path, True),
            (self.repo_path, True),
            (self.build_status_path, self.build_status_existed),
            (
                self.catalog_build_status_path,
                self.catalog_build_status_existed,
            ),
            (self.dictionary_path, self.dictionary_existed),
            (self.dictionary_backup_path, self.dictionary_backup_existed),
        )
        for path, existed in states:
            if existed:
                self._create_backup(path)
            else:
                self._create_absence_marker(path)

    def restore(self) -> None:
        """Restore inputs, status, and dictionary after all scenarios."""
        errors: list[str] = []
        restore_items = (
            (self.config_path, self.original_config_text),
            (self.catalog_path, self.original_catalog_text),
            (self.repo_path, self.original_repo_text),
        )
        for path, content in restore_items:
            try:
                self.write_text(path, content)
            except RuntimeError as exc:
                errors.append(str(exc))
        optional_items = (
            (
                self.build_status_path,
                self.build_status_existed,
                self.original_build_status_text,
            ),
            (
                self.catalog_build_status_path,
                self.catalog_build_status_existed,
                self.original_catalog_build_status_text,
            ),
            (
                self.dictionary_path,
                self.dictionary_existed,
                self.original_dictionary_text,
            ),
            (
                self.dictionary_backup_path,
                self.dictionary_backup_existed,
                self.original_dictionary_backup_text,
            ),
        )
        for path, existed, content in optional_items:
            try:
                if existed:
                    self.write_text(path, content)
                elif self.exists(path):
                    self.remove(path)
            except RuntimeError as exc:
                errors.append(str(exc))
        for path in self.created_output_paths:
            try:
                self.remove_tree(path)
            except RuntimeError as exc:
                errors.append(str(exc))

        # Preserve recovery metadata when restoration fails so the next run
        # can recover the pre-suite state.
        if not errors:
            for artifact in self.backup_paths + self.absence_markers:
                try:
                    self.remove(artifact)
                except RuntimeError as exc:
                    errors.append(str(exc))
        if not errors:
            try:
                self._prune_empty_recovery_directories()
            except RuntimeError as exc:
                errors.append(str(exc))
        if errors:
            raise RuntimeError("; ".join(errors))

    def baseline_is_restored(self) -> bool:
        """Return whether all mutable target files match their baseline."""
        required = (
            (self.config_path, self.original_config_text),
            (self.catalog_path, self.original_catalog_text),
            (self.repo_path, self.original_repo_text),
        )
        if any(self.read_text(path) != content for path, content in required):
            return False
        optional = (
            (
                self.build_status_path,
                self.build_status_existed,
                self.original_build_status_text,
            ),
            (
                self.dictionary_path,
                self.dictionary_existed,
                self.original_dictionary_text,
            ),
            (
                self.dictionary_backup_path,
                self.dictionary_backup_existed,
                self.original_dictionary_backup_text,
            ),
            (
                self.catalog_build_status_path,
                self.catalog_build_status_existed,
                self.original_catalog_build_status_text,
            ),
        )
        for path, existed, content in optional:
            if self.exists(path) != existed:
                return False
            if existed and self.read_text(path) != content:
                return False
        return all(not self.exists(path) for path in self.created_output_paths)

    # -- scenario preparation --------------------------------------------
    def restore_baseline_inputs(self) -> None:
        self.write_text(self.catalog_path, self.original_catalog_text)
        self.write_text(self.repo_path, self.original_repo_text)

    def configure(
        self,
        *,
        source: str = "catalog",
        engine: str = "image-builder",
        force_rebuild: bool = False,
        backup_s3_images: bool = False,
    ) -> None:
        config = deepcopy(self.original_config)
        config["functional_groups_source"] = source
        config["image_build_type"] = engine
        config.setdefault("build_image", {})["force_rebuild"] = force_rebuild
        config["build_image"]["backup_s3_images"] = backup_s3_images
        self.write_text(
            self.config_path,
            yaml.safe_dump(config, sort_keys=False),
        )

    def build(self) -> dict[str, Any]:
        """Run the real Image Build Manager build tag."""
        return run_playbook(tag="build", timeout=14400)

    @property
    def catalog(self) -> dict[str, Any]:
        return deepcopy(self.original_catalog)

    def expected_groups(self, catalog: dict[str, Any] | None = None) -> list[str]:
        root = (catalog or self.original_catalog).get("catalog", {})
        return [
            layer["name"]
            for layer in root.get("functionallayer", [])
            if isinstance(layer, dict)
            and str(layer.get("name", "")).endswith("_x86_64")
            and not str(layer.get("name", "")).startswith("baseos")
        ]

    @staticmethod
    def entry_engine(entry: dict[str, Any]) -> str:
        paths = " ".join(entry.get("s3_paths", {}).values())
        if "-imgbld/" in paths:
            return "image-builder"
        if "-imgth/" in paths:
            return "image-thrillhouse"
        return ""

    def engine_entries(
        self, document: dict[str, Any], engine: str
    ) -> dict[str, dict[str, Any]]:
        return {
            key: value
            for key, value in document.get("entries", {}).items()
            if self.entry_engine(value) == engine
        }

    def current_group_entries(
        self, document: dict[str, Any], engine: str
    ) -> dict[str, dict[str, Any]]:
        groups = set(self.expected_groups())
        result: dict[str, dict[str, Any]] = {}
        for entry in self.engine_entries(document, engine).values():
            group = entry.get("functional_group", "")
            if group in groups:
                previous = result.get(group)
                if previous is None or entry.get("last_used_at", "") >= previous.get(
                    "last_used_at", ""
                ):
                    result[group] = entry
        return result

    def all_artifacts_exist(self, entries: dict[str, dict[str, Any]]) -> bool:
        for entry in entries.values():
            for path in entry.get("s3_paths", {}).values():
                uri = path if str(path).startswith("s3://") else f"s3://{path}"
                if self.run_command(f"s3cmd info {shlex.quote(uri)}").rc != 0:
                    return False
        return True

    def s3_object_exists(self, uri: str) -> bool:
        """Return whether one exact S3 object exists."""
        return self.run_command(f"s3cmd info {shlex.quote(uri)}").rc == 0

    def recover_s3_artifact(self, artifact_uri: str, backup_uri: str) -> None:
        """Restore the exact pre-scenario artifact, then remove its backup."""
        if not self.s3_object_exists(backup_uri):
            return
        copied = self.run_command(
            f"s3cmd cp {shlex.quote(backup_uri)} "
            f"{shlex.quote(artifact_uri)}"
        )
        if copied.rc != 0 or not self.s3_object_exists(artifact_uri):
            raise RuntimeError(
                f"Unable to restore S3 artifact from: {backup_uri}"
            )
        deleted = self.run_command(f"s3cmd del {shlex.quote(backup_uri)}")
        if deleted.rc != 0 or self.s3_object_exists(backup_uri):
            raise RuntimeError(
                f"Unable to remove S3 recovery object: {backup_uri}"
            )

    def mutate_one_functional_group(self) -> tuple[dict[str, Any], str]:
        """Add one valid RPM alias to a group used by exactly one layer."""
        document = self.catalog
        root = document["catalog"]
        layers = [
            layer for layer in root["functionallayer"]
            if str(layer.get("name", "")).endswith("_x86_64")
        ]
        component_counts: dict[str, int] = {}
        for layer in layers:
            for component in layer.get("components", []):
                component_counts[component] = component_counts.get(component, 0) + 1

        target_layer = None
        group_name = ""
        for layer in layers:
            for component in layer.get("components", []):
                group = root.get("groups", {}).get(component)
                if (
                    component_counts.get(component) == 1
                    and isinstance(group, dict)
                    and isinstance(group.get("components"), list)
                ):
                    target_layer = layer
                    group_name = component
                    break
            if target_layer is not None:
                break

        if target_layer is None:
            raise RuntimeError(
                "Catalog has no x86_64 layer with a uniquely mutable group"
            )

        existing = set(root["groups"][group_name]["components"])
        package_alias = next(
            (
                alias
                for alias, package in root.get("packages", {}).items()
                if alias not in existing
                and isinstance(package, dict)
                and package.get("packagetype") == "rpm"
                and any(
                    source.get("architecture") == "x86_64"
                    for source in package.get("sources", [])
                    if isinstance(source, dict)
                )
            ),
            "",
        )
        if not package_alias:
            raise RuntimeError(
                "Catalog has no additional x86_64 RPM for selective mutation"
            )
        root["groups"][group_name]["components"].append(package_alias)
        return document, target_layer["name"]

    def mutate_repo_url(self) -> dict[str, Any]:
        document = deepcopy(self.original_repo)

        def update(value: Any) -> bool:
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == "url" and isinstance(child, str) and child:
                        value[key] = child.rstrip("/") if child.endswith("/") else child + "/"
                        return True
                    if update(child):
                        return True
            elif isinstance(value, list):
                for child in value:
                    if update(child):
                        return True
            return False

        if not update(document):
            raise RuntimeError("repo_status.yml contains no repository URL")
        return document

    def write_catalog(self, document: dict[str, Any]) -> None:
        self.write_text(
            self.catalog_path,
            json.dumps(document, indent=2) + "\n",
        )

    def write_repo(self, document: dict[str, Any]) -> None:
        self.write_text(
            self.repo_path,
            yaml.safe_dump(document, sort_keys=False),
        )

    def read_build_status(self, path: str | None = None) -> dict[str, Any]:
        status_path = path or f"{self.output_dir}/build_status.yml"
        return yaml.safe_load(self.read_text(status_path))

    def catalog_status_path(
        self, catalog: dict[str, Any] | None = None
    ) -> str:
        """Return the composite catalog-identity build-status path."""
        root = (catalog or self.original_catalog)["catalog"]
        image_group_id = f"{root['identifier']}-v{root['version']}"
        return f"{self.output_dir}/{image_group_id}/build_status.yml"


@pytest.fixture(scope="session")
def catalog_reuse_context(host, request):
    """Provide a live context and always restore modified runtime inputs."""
    context = CatalogReuseContext(host)
    request.addfinalizer(context.restore)
    return context
