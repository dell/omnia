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
"""End-to-end catalog dictionary reuse and rebuild-policy scenarios."""

from __future__ import annotations

import shlex

import pytest

from library.functions import TestLogger
from library.vars import TEST_CASES as TC


def _logger(case: str) -> TestLogger:
    tc = TC[case]
    return TestLogger(tc["title"], tc["id"])


def _require_build(result, logger: TestLogger) -> str:
    output = result.get("output", "")
    if result.get("success"):
        logger.info(
            f"Build completed in {result.get('duration', 0):.2f}s"
        )
    else:
        logger.failed("Image Build Manager build failed", result.get("error", ""))
    assert result.get("success"), result.get("error", "Build failed")
    return output


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.x86_64
@pytest.mark.order(1)
def test_catalog_first_build(catalog_reuse_context):
    """A dictionary miss builds every catalog functional group."""
    ctx = catalog_reuse_context
    tl = _logger("catalog_first_build")
    tl.check("Resetting the dictionary and running the first catalog build")
    ctx.restore_baseline_inputs()
    ctx.configure(engine="image-builder")
    ctx.save_dictionary(
        {"dictionary_version": 1, "entries": {}, "last_updated": ""}
    )

    _require_build(ctx.build(), tl)
    groups = set(ctx.expected_groups())
    entries = ctx.current_group_entries(
        ctx.load_dictionary(), "image-builder"
    )
    success = set(entries) == groups and ctx.all_artifacts_exist(entries)
    if success:
        tl.passed(
            f"Dictionary created with complete artifacts for {len(groups)} groups"
        )
    else:
        tl.failed("Dictionary entries or S3 artifacts are incomplete")
    assert success


@pytest.mark.deploy
@pytest.mark.sanity
@pytest.mark.x86_64
@pytest.mark.order(2)
def test_catalog_dictionary_reuse(catalog_reuse_context):
    """An identical catalog reuses every valid dictionary entry."""
    ctx = catalog_reuse_context
    tl = _logger("catalog_dictionary_reuse")
    ctx.restore_baseline_inputs()
    ctx.configure(engine="image-builder")
    before = ctx.current_group_entries(
        ctx.load_dictionary(), "image-builder"
    )
    timestamps = {
        group: entry.get("build_timestamp") for group, entry in before.items()
    }

    output = _require_build(ctx.build(), tl)
    after = ctx.current_group_entries(
        ctx.load_dictionary(), "image-builder"
    )
    reused = (
        len(before) == len(ctx.expected_groups())
        and output.count("DICTIONARY_HIT functional_group=")
        >= len(ctx.expected_groups())
        and all(
            after[group].get("build_timestamp") == timestamp
            for group, timestamp in timestamps.items()
        )
    )
    if reused:
        tl.passed("All catalog functional groups were reused without rebuilding")
    else:
        tl.failed("The identical catalog did not produce complete dictionary hits")
    assert reused


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.x86_64
@pytest.mark.order(3)
def test_catalog_selective_package_rebuild(catalog_reuse_context):
    """Changing one functional group rebuilds only that group."""
    ctx = catalog_reuse_context
    tl = _logger("catalog_selective_package_rebuild")
    ctx.restore_baseline_inputs()
    ctx.configure(engine="image-builder")
    changed_catalog, target_group = ctx.mutate_one_functional_group()
    before_keys = set(ctx.load_dictionary().get("entries", {}))
    ctx.write_catalog(changed_catalog)
    try:
        _require_build(ctx.build(), tl)
    finally:
        ctx.write_text(ctx.catalog_path, ctx.original_catalog_text)
    after = ctx.load_dictionary().get("entries", {})
    added = [after[key] for key in set(after) - before_keys]
    rebuilt_groups = {entry.get("functional_group") for entry in added}
    success = rebuilt_groups == {target_group}
    if success:
        tl.passed(f"Only {target_group} received a new package hash entry")
    else:
        tl.failed(f"Unexpected rebuilt groups: {sorted(rebuilt_groups)}")
    assert success


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.x86_64
@pytest.mark.order(4)
def test_catalog_repository_change_rebuild(catalog_reuse_context):
    """Changing repository configuration invalidates affected hashes."""
    ctx = catalog_reuse_context
    tl = _logger("catalog_repository_change_rebuild")
    ctx.restore_baseline_inputs()
    ctx.configure(engine="image-builder")
    changed_repo = ctx.mutate_repo_url()
    before_keys = set(ctx.load_dictionary().get("entries", {}))
    ctx.write_repo(changed_repo)
    try:
        _require_build(ctx.build(), tl)
    finally:
        ctx.write_text(ctx.repo_path, ctx.original_repo_text)
    after = ctx.load_dictionary().get("entries", {})
    rebuilt_groups = {
        after[key].get("functional_group")
        for key in set(after) - before_keys
        if ctx.entry_engine(after[key]) == "image-builder"
    }
    success = rebuilt_groups == set(ctx.expected_groups())
    if success:
        tl.passed("Repository configuration changed every dependent image hash")
    else:
        tl.failed(f"Unexpected repository rebuild set: {sorted(rebuilt_groups)}")
    assert success


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.x86_64
@pytest.mark.order(5)
def test_catalog_force_rebuild(catalog_reuse_context):
    """force_rebuild refreshes all current dictionary entries."""
    ctx = catalog_reuse_context
    tl = _logger("catalog_force_rebuild")
    ctx.restore_baseline_inputs()
    ctx.configure(engine="image-builder", force_rebuild=True)
    before = ctx.current_group_entries(
        ctx.load_dictionary(), "image-builder"
    )
    _require_build(ctx.build(), tl)
    after = ctx.current_group_entries(
        ctx.load_dictionary(), "image-builder"
    )
    refreshed = (
        set(after) == set(ctx.expected_groups())
        and all(
            after[group].get("build_timestamp")
            != before[group].get("build_timestamp")
            for group in before
        )
    )
    if refreshed:
        tl.passed("force_rebuild refreshed every catalog functional group")
    else:
        tl.failed("force_rebuild did not refresh all dictionary entries")
    assert refreshed


@pytest.mark.deploy
@pytest.mark.regression
@pytest.mark.x86_64
@pytest.mark.order(6)
def test_catalog_missing_artifact_rebuild(catalog_reuse_context):
    """A missing S3 object invalidates and rebuilds only its dictionary hit."""
    ctx = catalog_reuse_context
    tl = _logger("catalog_missing_artifact_rebuild")
    ctx.restore_baseline_inputs()
    ctx.configure(engine="image-builder")
    before = ctx.current_group_entries(
        ctx.load_dictionary(), "image-builder"
    )
    target_group = sorted(before)[0]
    target = before[target_group]
    artifact = target["s3_paths"]["rootfs"]
    artifact_uri = artifact if artifact.startswith("s3://") else f"s3://{artifact}"
    backup_uri = f"{artifact_uri}.catalog-reuse-backup"
    copied = ctx.run_command(
        f"s3cmd cp {shlex.quote(artifact_uri)} {shlex.quote(backup_uri)}"
    )
    assert copied.rc == 0, f"Unable to back up test artifact: {artifact_uri}"
    deleted = ctx.run_command(f"s3cmd del {shlex.quote(artifact_uri)}")
    assert deleted.rc == 0, f"Unable to remove test artifact: {artifact_uri}"
    try:
        _require_build(ctx.build(), tl)
    finally:
        if ctx.run_command(f"s3cmd info {shlex.quote(artifact_uri)}").rc != 0:
            ctx.run_command(
                f"s3cmd cp {shlex.quote(backup_uri)} {shlex.quote(artifact_uri)}"
            )
        ctx.run_command(f"s3cmd del {shlex.quote(backup_uri)}")
    after = ctx.current_group_entries(
        ctx.load_dictionary(), "image-builder"
    )
    rebuilt = (
        after[target_group].get("build_timestamp")
        != target.get("build_timestamp")
        and ctx.all_artifacts_exist({target_group: after[target_group]})
    )
    if rebuilt:
        tl.passed(f"Missing artifact caused {target_group} to rebuild")
    else:
        tl.failed(f"Missing artifact did not rebuild {target_group}")
    assert rebuilt


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.x86_64
@pytest.mark.order(7)
def test_catalog_switch_to_thrillhouse(catalog_reuse_context):
    """Switching engines creates distinct Thrillhouse dictionary entries."""
    ctx = catalog_reuse_context
    tl = _logger("catalog_switch_to_thrillhouse")
    ctx.restore_baseline_inputs()
    ctx.configure(engine="image-thrillhouse")
    before_keys = set(ctx.load_dictionary().get("entries", {}))
    _require_build(ctx.build(), tl)
    document = ctx.load_dictionary()
    added = [
        document["entries"][key]
        for key in set(document.get("entries", {})) - before_keys
    ]
    groups = {
        entry.get("functional_group")
        for entry in added
        if ctx.entry_engine(entry) == "image-thrillhouse"
    }
    success = groups == set(ctx.expected_groups())
    if success:
        tl.passed("Thrillhouse produced isolated dictionary and S3 artifacts")
    else:
        tl.failed(f"Unexpected Thrillhouse build set: {sorted(groups)}")
    assert success


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.x86_64
@pytest.mark.order(8)
def test_catalog_switch_to_image_builder(catalog_reuse_context):
    """Switching back selects only image-builder artifacts."""
    ctx = catalog_reuse_context
    tl = _logger("catalog_switch_to_image_builder")
    ctx.restore_baseline_inputs()
    ctx.configure(engine="image-builder")
    output = _require_build(ctx.build(), tl)
    status = ctx.read_build_status()
    paths = " ".join(
        value
        for arch in status.get("functional_group_images", [])
        for entries in arch.values()
        for entry in entries
        for key, value in entry.items()
        if key in {"kernel", "initrd", "image"}
    )
    success = (
        status.get("image_build_type") == "image-builder"
        and "-imgbld/" in paths
        and "-imgth/" not in paths
        and output.count("DICTIONARY_HIT functional_group=")
        >= len(ctx.expected_groups())
    )
    if success:
        tl.passed("Image Builder artifacts were selected without engine mixing")
    else:
        tl.failed("Build status mixed engines or missed dictionary reuse")
    assert success


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.x86_64
@pytest.mark.order(9)
def test_catalog_versioned_output(catalog_reuse_context):
    """A new catalog version writes a composite-identity status contract."""
    ctx = catalog_reuse_context
    tl = _logger("catalog_versioned_output")
    ctx.restore_baseline_inputs()
    ctx.configure(engine="image-builder")
    document = ctx.catalog
    root = document["catalog"]
    new_version = f"{root.get('version', '1.0')}-catalog-reuse"
    root["version"] = new_version
    image_group_id = f"{root['identifier']}-v{new_version}"
    status_dir = f"{ctx.output_dir}/{image_group_id}"
    ctx.created_output_paths.add(status_dir)
    ctx.write_catalog(document)
    try:
        _require_build(ctx.build(), tl)
        status_path = f"{status_dir}/build_status.yml"
        catalog_status = ctx.read_build_status(status_path)
        latest_status_path = f"{ctx.output_dir}/build_status.yml"
        latest_status = ctx.read_build_status(latest_status_path)
        success = (
            ctx.exists(status_path)
            and ctx.exists(latest_status_path)
            and catalog_status == latest_status
            and catalog_status.get("overall_status") == "success"
            and catalog_status.get("image_build_type") == "image-builder"
        )
    finally:
        ctx.write_text(ctx.catalog_path, ctx.original_catalog_text)
    if success:
        tl.passed(
            "Latest and catalog-versioned status files match for "
            f"{image_group_id}"
        )
    else:
        tl.failed(f"Versioned build status missing for {image_group_id}")
    assert success


@pytest.mark.deploy
@pytest.mark.regression
@pytest.mark.x86_64
@pytest.mark.order(10)
def test_config_mode_cache_isolation(catalog_reuse_context):
    """Config mode uses its local cache and never updates the dictionary."""
    ctx = catalog_reuse_context
    tl = _logger("config_mode_cache_isolation")
    ctx.restore_baseline_inputs()
    ctx.configure(
        source="config",
        engine="image-builder",
        backup_s3_images=True,
    )
    catalog_status_path = ctx.catalog_status_path()
    catalog_status_before = (
        ctx.read_text(catalog_status_path)
        if ctx.exists(catalog_status_path)
        else None
    )
    before = ctx.load_dictionary()
    output = _require_build(ctx.build(), tl)
    after = ctx.load_dictionary()
    status = ctx.read_build_status()
    catalog_status_after = (
        ctx.read_text(catalog_status_path)
        if ctx.exists(catalog_status_path)
        else None
    )
    success = (
        before == after
        and "DICTIONARY_HIT functional_group=" not in output
        and status.get("overall_status") == "success"
        and ctx.exists(f"{ctx.output_dir}/build_status.yml")
        and catalog_status_after == catalog_status_before
    )
    if success:
        tl.passed("Config mode remained independent of the global dictionary")
    else:
        tl.failed("Config mode modified or consulted the global dictionary")
    assert success
