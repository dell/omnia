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

    pre = restart.index("name: Calculate BuildStream effective PXE inventory")
    pxe = restart.index("orchestrator/playbooks/pxeboot/pxeboot.yml")
    post = restart.index("name: Persist BuildStream PXE restart results")

    assert pre < pxe < post
    assert "defer_pxe_failure: true" in restart
    assert "not (bsm_skip_pxe | default(false) | bool)" in restart
    assert not (_RESTART_DIR / "pre_pxe.yml").exists()
    assert not (_RESTART_DIR / "post_pxe.yml").exists()


def test_orchestrator_pxe_has_no_buildstream_processing():
    """The normal Orchestrator PXE playbook remains domain-independent."""
    pxe = _read(_ORCHESTRATOR_PXE)
    reporting = _read(_PXE_REPORTING)

    assert "pxe_buildstream_manager" not in pxe
    assert "pxe_buildstream_manager" not in reporting
    assert "defer_pxe_failure" in reporting


def test_pre_pxe_uses_restart_state_retry_inventory():
    """Pre-PXE delegates retry filtering to the BuildStream role."""
    restart = _read(_RESTART_DIR / "restart.yml")
    effective = _read(
        _SRC
        / "build_stream"
        / "roles"
        / "pxe_buildstream_manager"
        / "tasks"
        / "generate_effective_csv.yml"
    )

    assert "tasks_from: generate_effective_csv.yml" in restart
    assert "restart_state.json" in effective
    assert "failed_nodes.json" in effective
    assert "difference(bsm_booted_ips)" in effective


def test_post_pxe_orders_persistence_and_preserves_pxe_failure():
    """Post-PXE persists every artifact before restoring failure precedence."""
    restart = _read(_RESTART_DIR / "restart.yml")

    write_results = restart.index("tasks_from: write_node_results.yml")
    update_state = restart.index("tasks_from: update_restart_state.yml")
    register_gitlab = restart.index("tasks_from: gitlab_host.yml")
    upload = restart.index("tasks_from: upload_to_gitlab.yml")
    original_failure = restart.index("name: Preserve original Orchestrator PXE failure")
    post_failure = restart.index("name: Report BuildStream post-PXE failure")

    assert write_results < update_state < register_gitlab < upload
    assert upload < original_failure < post_failure
    assert "not (pxeboot_failed | default(false) | bool)" in restart


def test_restart_playbooks_require_buildstream_and_job_id():
    """All BuildStream restart plays fail closed without valid context."""
    restart = _read(_RESTART_DIR / "restart.yml")

    assert restart.count("Stop when BuildStream restart context is absent") == 2
    assert restart.count("enable_build_stream") >= 3
    assert restart.count("job_id") >= 6
    assert restart.count("length") >= 3
    assert restart.count("^[0-9a-fA-F-]+$") >= 3
