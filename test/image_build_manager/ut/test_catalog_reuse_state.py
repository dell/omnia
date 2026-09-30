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
"""Unit tests for catalog-reuse target-state restoration."""

# Test helpers intentionally exercise private recovery primitives and use
# descriptive function names instead of repeating them in docstrings.
# pylint: disable=missing-function-docstring,protected-access,unnecessary-lambda

from types import SimpleNamespace

import pytest

from fvt.build.catalog_reuse.conftest import CatalogReuseContext


def _restore_context(build_status_existed):
    context = object.__new__(CatalogReuseContext)
    context.config_path = "/data/input/image_build_config.yml"
    context.catalog_path = "/data/catalog.json"
    context.repo_path = "/data/repo_status.yml"
    context.build_status_path = "/data/output/build_status.yml"
    context.catalog_build_status_path = (
        "/data/output/catalog-v1.0/build_status.yml"
    )
    context.dictionary_path = "/data/output/image_group_dictionary.json"
    context.dictionary_backup_path = f"{context.dictionary_path}.bak"
    context.output_dir = "/data/output"

    context.original_config_text = "original config"
    context.original_catalog_text = "original catalog"
    context.original_repo_text = "original repo status"
    context.build_status_existed = build_status_existed
    context.original_build_status_text = "original build status"
    context.catalog_build_status_existed = True
    context.original_catalog_build_status_text = "original catalog status"
    context.dictionary_existed = False
    context.original_dictionary_text = ""
    context.dictionary_backup_existed = False
    context.original_dictionary_backup_text = ""
    context.created_output_paths = set()
    context.backup_paths = []
    context.absence_markers = []

    files = {
        context.config_path: "modified config",
        context.catalog_path: "modified catalog",
        context.repo_path: "modified repo status",
        context.build_status_path: "scenario build status",
        context.catalog_build_status_path: "scenario catalog status",
    }
    context.exists = lambda path: path in files
    context.write_text = lambda path, content: files.__setitem__(path, content)
    context.remove = lambda path: files.pop(path, None)
    context.remove_tree = lambda path: files.pop(path, None)
    context.run_command = lambda command: SimpleNamespace(rc=0)
    return context, files


def test_restore_reinstates_original_build_status():
    context, files = _restore_context(build_status_existed=True)

    context.restore()

    assert files[context.config_path] == "original config"
    assert files[context.catalog_path] == "original catalog"
    assert files[context.repo_path] == "original repo status"
    assert files[context.build_status_path] == "original build status"
    assert (
        files[context.catalog_build_status_path]
        == "original catalog status"
    )


def test_restore_removes_build_status_created_by_scenarios():
    context, files = _restore_context(build_status_existed=False)

    context.restore()

    assert context.build_status_path not in files


def test_restore_failure_preserves_recovery_artifacts():
    context, files = _restore_context(build_status_existed=True)
    backup = f"{context.config_path}.catalog-reuse-backup"
    context.backup_paths = [backup]
    files[backup] = "original config"
    original_write = context.write_text

    def fail_config_write(path, content):
        if path == context.config_path:
            raise RuntimeError("simulated restore failure")
        original_write(path, content)

    context.write_text = fail_config_write

    with pytest.raises(RuntimeError, match="simulated restore failure"):
        context.restore()

    assert backup in files


def test_stale_absence_marker_recovers_absent_baseline():
    context, files = _restore_context(build_status_existed=False)
    marker = context._absence_marker_path(context.build_status_path)
    files[marker] = ""

    context._recover_runtime_state(context.build_status_path)

    assert context.build_status_path not in files
    assert marker not in files


def test_stale_backup_recovers_baseline_before_snapshot():
    context, files = _restore_context(build_status_existed=True)
    backup = context._backup_path(context.config_path)
    files[context.config_path] = "interrupted scenario config"
    files[backup] = "pre-suite config"

    def copy_backup(command):
        if command.startswith("cp -f --"):
            files[context.config_path] = files[backup]
        return SimpleNamespace(rc=0)

    context.run_command = copy_backup

    context._recover_runtime_state(context.config_path)

    assert files[context.config_path] == "pre-suite config"
    assert backup not in files

    artifact_uri = "s3://boot-images/group/image/rootfs"
    artifact_backup_uri = f"{artifact_uri}.catalog-reuse-backup"
    objects = {
        artifact_uri: "rebuilt artifact",
        artifact_backup_uri: "original artifact",
    }
    context.s3_object_exists = lambda uri: uri in objects

    def recover_s3(command):
        if command.startswith("s3cmd cp"):
            objects[artifact_uri] = objects[artifact_backup_uri]
        elif command.startswith("s3cmd del"):
            objects.pop(artifact_backup_uri, None)
        return SimpleNamespace(rc=0)

    context.run_command = recover_s3
    context.recover_s3_artifact(artifact_uri, artifact_backup_uri)

    assert objects[artifact_uri] == "original artifact"
    assert artifact_backup_uri not in objects
