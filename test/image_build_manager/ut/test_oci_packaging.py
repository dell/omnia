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
Image Build Manager — OCI packaging contract (TC-UT-009, created source).

The org.opencontainers.image.created annotation is taken from each functional
group's local image config, so repeated publication of the same image keeps the
same value. The shared publish-time now() value is not used.
"""

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
TASKS = REPO_ROOT / "src/image_build_manager/roles/build_os_images/tasks"
RFC3339_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
READ_TASK = "Read the image config created time of the local OCI image"


def _leaf_tasks(tasks):
    """Yield every leaf task, descending into block, rescue, and always."""
    for task in tasks:
        nested = [section for section in ("block", "rescue", "always") if section in task]
        for section in nested:
            yield from _leaf_tasks(task[section])
        if not nested:
            yield task


def _load(name):
    return yaml.safe_load((TASKS / name).read_text(encoding="utf-8")) or []


def test_publish_step_has_no_shared_publish_time_created_value():
    """The publish-time now() value that every group shared is removed."""
    text = (TASKS / "publish_oci_images.yml").read_text(encoding="utf-8")
    assert "_ext_oci_created" not in text
    assert "now(utc=true)" not in text


def test_created_is_read_per_group_from_the_local_image_config():
    """Each group reads its own image config created time before annotating."""
    leaves = list(_leaf_tasks(_load("publish_oci_image.yml")))
    names = [task.get("name") for task in leaves]
    read = [task for task in leaves if task.get("name") == READ_TASK]
    assert len(read) == 1
    argv = read[0]["ansible.builtin.command"]["argv"]
    assert argv[:3] == ["{{ ext_oci_regctl_bin }}", "image", "config"]
    assert "{{ _fg_local_ref }}" in argv
    assert names.index(READ_TASK) < names.index("Annotate the local OCI image with provenance")


def test_annotation_uses_the_per_group_created_value():
    """The created annotation is the value read for this group, not a shared variable."""
    text = (TASKS / "publish_oci_image.yml").read_text(encoding="utf-8")
    assert 'org.opencontainers.image.created: "{{ _fg_created }}"' in text
    assert "set_fact" in text and "_fg_created:" in text


def test_created_value_format_is_rfc3339_utc():
    """The stored value matches the RFC 3339 UTC form the annotation expects."""
    sample = "2026-11-15T15:31:57Z"
    assert RFC3339_UTC.match(sample)
    assert not RFC3339_UTC.match("2026-11-28T10:00:00.123456789+00:00")
