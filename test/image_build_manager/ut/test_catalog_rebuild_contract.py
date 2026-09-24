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
"""Source-contract tests for catalog reuse and config-mode isolation."""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
TASKS = REPO_ROOT / "src/image_build_manager/roles/build_os_images/tasks"


def _task(name):
    return (TASKS / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("architecture", ["x86_64", "aarch64"])
def test_compute_hash_includes_repository_and_engine(architecture):
    content = _task(f"build_compute_image_{architecture}.yml")
    assert "~ '|repos:' ~ _repo_config_hash" in content
    assert "~ '|image_build_type:' ~ _image_build_type" in content


@pytest.mark.parametrize("architecture", ["x86_64", "aarch64"])
def test_dictionary_lookup_is_catalog_only_and_force_aware(architecture):
    content = _task(f"build_compute_image_{architecture}.yml")
    assert "operation: lookup" in content
    assert "_pkg_source == 'catalog'" in content
    assert "not (force_rebuild | default(false) | bool)" in content


@pytest.mark.parametrize("architecture", ["x86_64", "aarch64"])
def test_previous_hash_cache_is_config_mode_only(architecture):
    content = _task(f"build_compute_image_{architecture}.yml")
    assert "Check previous compute image package hashes" in content
    assert "Save compute image package hashes" in content
    assert content.count("_pkg_source == 'config'") >= 4


@pytest.mark.parametrize("architecture", ["x86_64", "aarch64"])
def test_s3_previous_backup_is_config_mode_only(architecture):
    content = _task(f"build_compute_image_{architecture}.yml")
    assert content.count("backup_s3_images | default(false) | bool") >= 2
    assert content.count("_pkg_source == 'config'") >= 4


def test_catalog_status_uses_composite_identity_directory():
    content = _task("write_build_status.yml")
    assert "_status_catalog_identifier ~ '-v' ~ _status_catalog_version" in content
    assert "_output_domain ~ '/build_status.yml'" in content


def test_latest_project_status_is_written_for_every_mode():
    content = _task("write_build_status.yml")
    assert "Write latest project-level build_status.yml" in content
    assert 'dest: "{{ _output_base }}/build_status.yml"' in content
    assert "when: _catalog_status_output | bool" not in content.split(
        "Write latest project-level build_status.yml", 1
    )[1].split("Write catalog-version build_status.yml", 1)[0]


def test_catalog_status_copy_is_catalog_mode_only():
    content = _task("write_build_status.yml")
    catalog_task = content.split(
        "Write catalog-version build_status.yml", 1
    )[1].split("Build versioned output path", 1)[0]
    assert 'dest: "{{ _output_domain }}/build_status.yml"' in catalog_task
    assert "when: _catalog_status_output | bool" in catalog_task


def test_successful_catalog_build_upserts_dictionary():
    content = _task("main.yml")
    assert "operation: upsert" in content
    assert "_pkg_source == 'catalog'" in content
    assert "catalog_schema_version:" in content


def test_dictionary_hits_require_complete_s3_artifacts():
    content = _task("validate_dictionary_hits.yml")
    assert "entry.s3_paths.items()" in content
    assert "s3cmd" in content
    assert "invalid_groups" in content


def test_force_rebuild_is_the_only_rebuild_control():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for domain in ("image_build_manager", "build_stream")
        for path in (REPO_ROOT / "src" / domain).rglob("*")
        if path.suffix in {".py", ".yml", ".yaml", ".json", ".md"}
    )
    assert "build_execution_mode" not in source
