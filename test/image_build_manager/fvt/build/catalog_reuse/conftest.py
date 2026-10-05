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
import json
import os
import shlex
from typing import Any

import pytest
import yaml

from library.functions import run_playbook
from omnia_auto import read_remote_env, resolve_domain_data_path


DOMAIN = "image_build_manager"
EMPTY_DICTIONARY = {
    "dictionary_version": 1,
    "entries": {},
    "last_updated": "",
}


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
        self.catalog_path = read_remote_env(host, "CATALOG_FILE_PATH")
        self.config_path = (
            f"{self.data_root}/input/{self.project}/image_build_config.yml"
        )
        self.output_dir = f"{self.data_root}/output/{self.project}"
        self.dictionary_path = f"{self.output_dir}/image_group_dictionary.json"
        self.dictionary_backup_path = f"{self.dictionary_path}.bak"

        self.original_config_text = self.read_text(self.config_path)
        self.original_catalog_text = self.read_text(self.catalog_path)
        self.original_config = yaml.safe_load(self.original_config_text)
        self.original_catalog = json.loads(self.original_catalog_text)
        self.repo_path = self.original_config["repo_manager_output_path"]
        self.original_repo_text = self.read_text(self.repo_path)
        self.original_repo = yaml.safe_load(self.original_repo_text)
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
        self.created_output_paths: set[str] = set()
        self.backup_paths: list[str] = []
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
    def _create_backup(self, path: str) -> None:
        backup = f"{path}.catalog-reuse-backup"
        # A stale backup means a prior test was interrupted. Restore it first.
        if self.exists(backup):
            result = self.run_command(
                f"cp -f -- {shlex.quote(backup)} {shlex.quote(path)}"
            )
            if result.rc != 0:
                raise RuntimeError(f"Unable to recover stale backup: {backup}")
        result = self.run_command(
            f"cp -f -- {shlex.quote(path)} {shlex.quote(backup)}"
        )
        if result.rc != 0:
            raise RuntimeError(f"Unable to create runtime backup: {path}")
        self.backup_paths.append(backup)

    def _create_runtime_backups(self) -> None:
        for path in (self.config_path, self.catalog_path, self.repo_path):
            self._create_backup(path)
        if self.dictionary_existed:
            self._create_backup(self.dictionary_path)
        if self.dictionary_backup_existed:
            self._create_backup(self.dictionary_backup_path)

    def restore(self) -> None:
        """Restore inputs and dictionary even when a scenario failed."""
        restore_items = (
            (self.config_path, self.original_config_text),
            (self.catalog_path, self.original_catalog_text),
            (self.repo_path, self.original_repo_text),
        )
        for path, content in restore_items:
            try:
                self.write_text(path, content)
            except RuntimeError:
                pass
        try:
            if self.dictionary_existed:
                self.write_text(
                    self.dictionary_path, self.original_dictionary_text
                )
            elif self.exists(self.dictionary_path):
                self.remove(self.dictionary_path)
            if self.dictionary_backup_existed:
                self.write_text(
                    self.dictionary_backup_path,
                    self.original_dictionary_backup_text,
                )
            elif self.exists(self.dictionary_backup_path):
                self.remove(self.dictionary_backup_path)
        except RuntimeError:
            pass
        for path in self.created_output_paths:
            self.run_command(f"rm -rf -- {shlex.quote(path)}")
        for backup in self.backup_paths:
            self.run_command(f"rm -f -- {shlex.quote(backup)}")

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

    def mutate_one_functional_group(self) -> tuple[dict[str, Any], str]:
        """Add one valid RPM alias to a group unique to the first layer."""
        document = self.catalog
        root = document["catalog"]
        layers = [
            layer for layer in root["functionallayer"]
            if str(layer.get("name", "")).endswith("_x86_64")
        ]
        target_layer = layers[0]
        component_counts: dict[str, int] = {}
        for layer in layers:
            for component in layer.get("components", []):
                component_counts[component] = component_counts.get(component, 0) + 1
        group_name = next(
            component for component in target_layer.get("components", [])
            if component_counts.get(component) == 1
            and isinstance(root.get("groups", {}).get(component), dict)
            and isinstance(root["groups"][component].get("components"), list)
        )
        existing = set(root["groups"][group_name]["components"])
        package_alias = next(
            alias for alias, package in root.get("packages", {}).items()
            if alias not in existing
            and isinstance(package, dict)
            and package.get("packagetype") == "rpm"
            and any(
                source.get("architecture") == "x86_64"
                for source in package.get("sources", [])
                if isinstance(source, dict)
            )
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
