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
"""
Regression tests for OMN-DEF #867.

iso_creation's "Check if NFS is already mounted" task used to match purely on
NFS *server* (``mount | grep '<server>:'``), so if the server already had an
unrelated or child export mounted, the role believed the target directory was
already mounted, skipped auto-mounting, and path resolution later failed with
"doesn't match any mounted export".

The fix adds a "Filter existing mounts to the ones whose export covers the
requested NFS directory" task. These tests render that exact Jinja2 template
(extracted live from tasks/main.yml, not a hand copy) against representative
mount-table scenarios to pin the behavior in place.
"""

# pylint: disable=missing-function-docstring,redefined-outer-name

import jinja2
import pytest
import yaml


def _load_filter_template(src_dir):
    """Pull the live Jinja template string out of tasks/main.yml."""
    tasks_path = src_dir / "roles" / "iso_creation" / "tasks" / "main.yml"
    with open(tasks_path, encoding="utf-8") as handle:
        tasks = yaml.safe_load(handle)

    filter_task = next(
        task
        for task in tasks
        if task.get("name")
        == "Filter existing mounts to the ones whose export covers the "
        "requested NFS directory"
    )
    return filter_task["ansible.builtin.set_fact"]["_nfs_matching_mounts"]


@pytest.fixture
def render_matching_mounts(src_dir):
    template_str = _load_filter_template(src_dir)
    env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
    template = env.from_string(template_str)

    def _render(mount_lines, nfs_dir):
        # Mirrors the shape of the real Ansible-registered command result
        # (a dict with a stdout_lines key), which the template accesses via
        # `_nfs_mounts.stdout_lines`.
        return template.render(
            _nfs_mounts={"stdout_lines": mount_lines}, _nfs_dir=nfs_dir
        ).strip()

    return _render


def test_unrelated_child_export_is_not_treated_as_already_mounted(
    render_matching_mounts,
):
    # Reported scenario: server already has an export mounted at a sibling
    # child path (/mnt/nfsuser/rohit/slurm) but the target dir
    # (/mnt/nfsuser/rohit/iso) is not under it.
    mounts = ["server1:/mnt/nfsuser/rohit/slurm /tmp/some_other_mount"]
    result = render_matching_mounts(mounts, "/mnt/nfsuser/rohit/iso")
    assert result == ""


def test_exact_export_match_is_recognized_as_mounted(render_matching_mounts):
    mounts = ["server1:/mnt/nfsuser/rohit /tmp/install_os_nfs"]
    result = render_matching_mounts(mounts, "/mnt/nfsuser/rohit")
    assert result == "server1:/mnt/nfsuser/rohit /tmp/install_os_nfs"


def test_parent_export_covers_child_target_directory(render_matching_mounts):
    mounts = ["server1:/mnt/nfsuser/rohit /tmp/install_os_nfs"]
    result = render_matching_mounts(mounts, "/mnt/nfsuser/rohit/iso/sub")
    assert result == "server1:/mnt/nfsuser/rohit /tmp/install_os_nfs"


def test_lookalike_sibling_export_is_not_a_false_prefix_match(
    render_matching_mounts,
):
    # /mnt/nfsuser/rohit2 shares a string prefix with /mnt/nfsuser/rohit but
    # is not actually a parent directory of it.
    mounts = ["server1:/mnt/nfsuser/rohit2 /tmp/other_mount"]
    result = render_matching_mounts(mounts, "/mnt/nfsuser/rohit/iso")
    assert result == ""


def test_no_mounts_at_all_yields_empty_result(render_matching_mounts):
    result = render_matching_mounts([], "/mnt/nfsuser/rohit")
    assert result == ""
