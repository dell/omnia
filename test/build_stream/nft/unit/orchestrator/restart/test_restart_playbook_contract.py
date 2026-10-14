# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Static contracts for the BuildStream restart playbook sequence."""

from pathlib import Path


_SRC = Path(__file__).resolve().parents[6] / "src"
_RESTART_DIR = _SRC / "build_stream" / "playbooks" / "restart"
_ORCHESTRATOR_PXE = (
    _SRC / "orchestrator" / "playbooks" / "pxeboot" / "pxeboot.yml"
)
_PXE_REPORTING = (
    _SRC / "orchestrator" / "roles" / "pxe_boot_reporting" / "tasks" / "main.yml"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_restart_sequence_orders_pre_pxe_orchestrator_and_post_pxe():
    """BuildStream owns a deterministic three-step restart sequence."""
    restart = _read(_RESTART_DIR / "restart.yml")

    pre = restart.index("import_playbook: pre_pxe.yml")
    pxe = restart.index("orchestrator/playbooks/pxeboot/pxeboot.yml")
    post = restart.index("import_playbook: post_pxe.yml")

    assert pre < pxe < post
    assert "defer_pxe_failure: true" in restart
    assert "not (bsm_skip_pxe | default(false) | bool)" in restart
    assert "when: *buildstream_restart_enabled" in restart


def test_orchestrator_pxe_has_no_buildstream_processing():
    """The normal Orchestrator PXE playbook remains domain-independent."""
    pxe = _read(_ORCHESTRATOR_PXE)
    reporting = _read(_PXE_REPORTING)

    assert "pxe_buildstream_manager" not in pxe
    assert "pxe_buildstream_manager" not in reporting
    assert "defer_pxe_failure" in reporting


def test_pre_pxe_uses_restart_state_retry_inventory():
    """Pre-PXE delegates retry filtering to the BuildStream role."""
    pre = _read(_RESTART_DIR / "pre_pxe.yml")
    effective = _read(
        _SRC
        / "build_stream"
        / "roles"
        / "pxe_buildstream_manager"
        / "tasks"
        / "generate_effective_csv.yml"
    )

    assert "tasks_from: generate_effective_csv.yml" in pre
    assert "restart_state.json" in effective
    assert "failed_nodes.json" in effective
    assert "difference(bsm_booted_ips)" in effective


def test_post_pxe_orders_persistence_and_preserves_pxe_failure():
    """Post-PXE persists every artifact before restoring failure precedence."""
    post = _read(_RESTART_DIR / "post_pxe.yml")

    write_results = post.index("tasks_from: write_node_results.yml")
    update_state = post.index("tasks_from: update_restart_state.yml")
    register_gitlab = post.index("tasks_from: gitlab_host.yml")
    upload = post.index("tasks_from: upload_to_gitlab.yml")
    original_failure = post.index("name: Preserve original Orchestrator PXE failure")
    post_failure = post.index("name: Report BuildStream post-PXE failure")

    assert write_results < update_state < register_gitlab < upload
    assert upload < original_failure < post_failure
    assert "not (pxeboot_failed | default(false) | bool)" in post


def test_restart_playbooks_require_buildstream_and_job_id():
    """All BuildStream restart playbooks fail closed without valid context."""
    for name in ("restart.yml", "pre_pxe.yml", "post_pxe.yml"):
        content = _read(_RESTART_DIR / name)
        assert "enable_build_stream" in content
        assert "job_id" in content
        assert "length" in content
        assert "^[0-9a-fA-F-]+$" in content
