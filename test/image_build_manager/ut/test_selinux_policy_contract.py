# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Static contracts for the Image Build Manager SELinux compatibility policy."""

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[3]
_IBM = _ROOT / "src" / "image_build_manager"
_ROLE = _IBM / "roles" / "build_os_images"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_policy_allows_watcher_runtime_transition_and_bpf_execution():
    policy = _read(_ROLE / "files" / "omnia-crun-bpf.te")

    assert "module omnia-crun-bpf 1.1;" in policy
    assert "allow init_t container_runtime_t:bpf prog_run;" in policy
    assert "allow unconfined_service_t container_runtime_t:process2" in policy
    assert "nnp_transition" in policy
    assert "nosuid_transition" in policy


def test_policy_refresh_uses_managed_checksum_and_records_after_install():
    preflight = _read(_ROLE / "tasks" / "preflight_selinux_check.yml")

    checksum = preflight.index("Calculate managed SELinux policy checksum")
    refresh = preflight.index("Determine whether SELinux policy refresh is required")
    install = preflight.index("name: Load SELinux policy module")
    verify = preflight.index("name: Verify omnia-crun-bpf SELinux module is enabled")
    marker = preflight.index("name: Record installed SELinux policy checksum")

    assert checksum < refresh < install < verify < marker
    assert "not _selinux_policy_checksum_marker.stat.exists" in preflight
    assert "!= _selinux_policy_checksum" in preflight


def test_policy_installation_fails_early_when_selinux_is_enforcing():
    preflight = _read(_ROLE / "tasks" / "preflight_selinux_check.yml")

    assert "name: Check SELinux enforcement state" in preflight
    assert "name: Fail when SELinux policy installation fails while enforcing" in preflight
    assert "== 'Enforcing'" in preflight


def test_local_prepare_installs_policy_before_podman_roles():
    prepare = _read(_IBM / "playbooks" / "prepare" / "prepare_image_build_manager.yml")

    policy = prepare.index("tasks_from: preflight_selinux_check.yml")
    minio = prepare.index("name: deploy_minio")
    registry = prepare.index("name: deploy_registry")

    assert policy < minio < registry


def test_build_execute_installs_policy_before_builder_image_lookup():
    main = _read(_ROLE / "tasks" / "main.yml")

    policy = main.index("include_tasks: preflight_selinux_check.yml")
    builder = main.index("include_tasks: prepare_repo_builder_image.yml")

    assert policy < builder


def test_aarch64_preparation_installs_policy_before_podman_lookup():
    prepare = _read(_IBM / "roles" / "prepare_aarch64_node" / "tasks" / "main.yml")

    policy = prepare.index("tasks_from: preflight_selinux_check.yml")
    podman = prepare.index("containers.podman.podman_image_info:")

    assert policy < podman
