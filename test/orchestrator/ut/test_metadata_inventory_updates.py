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

"""Contracts for per-host metadata updates of the common Metadata Service groups.

The common ``ssh`` group carries ``host_mount_map``, one entry per host. Adding
a node adds an entry, which changes the group. That must be reported as an
inventory update that names the hosts it concerns, not as a group-wide update,
or every node of the cluster is marked for reprovision.
"""

# pylint: disable=wrong-import-position,protected-access

import json
import sys
from pathlib import Path

import pytest

_SRC_PLUGIN_ROOT = str(
    Path(__file__).resolve().parents[3] / "src" / "orchestrator" / "plugins"
)
if _SRC_PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _SRC_PLUGIN_ROOT)

try:
    from module_utils.openchami.reconciler import OpenChamiReconciler
except ModuleNotFoundError as error:
    pytest.skip(
        f"OpenCHAMI reconciler module is unavailable: {error}",
        allow_module_level=True,
    )

PROJECT = "project_default"
GROUP = "ssh"
TEMPLATE = "ssh_pwauth: true\n"


def _mounts(*hosts, source="nfs:/share"):
    """Return the host_mount_map value (JSON text, as the playbook stores it)."""
    return json.dumps({host: {"mounts": [[source, "/mnt"]]} for host in hosts})


def _spec(host_map=None, template=TEMPLATE, extra=None):
    meta = dict(extra or {})
    if host_map is not None:
        meta["host_mount_map"] = host_map
    return {"description": "ssh config", "template": template, "metaData": meta}


class FakeMetadata:
    """In-memory Metadata Service that keeps what the reconciler writes."""

    def __init__(self, groups):
        self.stored = {
            name: {
                "metadata": {
                    "name": name,
                    "uid": f"uid-{name}",
                    "labels": OpenChamiReconciler._ownership_labels(PROJECT),
                },
                "spec": spec,
            }
            for name, spec in groups.items()
        }
        self.updates = []

    def groups(self):
        """Return the stored groups."""
        return list(self.stored.values())

    def create_group(self, payload):
        """Store a new group."""
        name = payload["metadata"]["name"]
        self.stored[name] = {
            "metadata": {**payload["metadata"], "uid": f"uid-{name}"},
            "spec": payload["spec"],
        }

    def update_group(self, uid, payload):
        """Replace a group and remember the write."""
        name = payload["metadata"]["name"]
        self.updates.append(name)
        self.stored[name] = {
            "metadata": {**payload["metadata"], "uid": uid},
            "spec": payload["spec"],
        }


def _reconcile(current, desired):
    metadata = FakeMetadata({GROUP: current})
    reconciler = object.__new__(OpenChamiReconciler)
    reconciler.metadata = metadata
    result = reconciler.reconcile_metadata_groups(
        [{"metadata": {"name": GROUP}, "spec": desired}], PROJECT
    )
    return result, metadata


def test_adding_a_node_is_an_inventory_update_for_that_node_only():
    """A new host entry names the new host and is not a group-wide update."""
    result, metadata = _reconcile(
        _spec(_mounts("node1", "node2")), _spec(_mounts("node1", "node2", "node3"))
    )

    assert result["inventory_updated"] == {GROUP: ["node3"]}
    assert not result["updated"]
    assert not result["created"]
    assert result["changed"] is True
    assert metadata.updates == [GROUP], "the group must still be written"


def test_editing_one_hosts_entry_names_only_that_host():
    """Only the host whose entry changed is reported."""
    result, _ = _reconcile(
        _spec(_mounts("node1", "node2")),
        _spec(json.dumps({
            "node1": {"mounts": [["nfs:/share", "/mnt"]]},
            "node2": {"mounts": [["nfs:/other", "/mnt"]]},
        })),
    )

    assert result["inventory_updated"] == {GROUP: ["node2"]}
    assert not result["updated"]


def test_removing_a_node_updates_the_group_without_naming_any_host():
    """A removed host has no node left to reprovision."""
    result, metadata = _reconcile(
        _spec(_mounts("node1", "node2")), _spec(_mounts("node1"))
    )

    assert result["inventory_updated"] == {GROUP: []}
    assert not result["updated"]
    assert metadata.updates == [GROUP]


def test_first_host_map_names_every_host():
    """When the map first appears, every host in it is concerned."""
    result, _ = _reconcile(_spec(None), _spec(_mounts("node1", "node2")))

    assert result["inventory_updated"] == {GROUP: ["node1", "node2"]}
    assert not result["updated"]


@pytest.mark.parametrize(
    "current,desired",
    [
        (
            _spec(_mounts("node1"), template="old: 1\n"),
            _spec(_mounts("node1", "node2"), template="new: 2\n"),
        ),
        (
            _spec(_mounts("node1"), extra={"cluster": "a"}),
            _spec(_mounts("node1", "node2"), extra={"cluster": "b"}),
        ),
        (
            _spec(_mounts("node1")),
            {**_spec(_mounts("node1", "node2")), "description": "changed"},
        ),
    ],
    ids=["template", "other-metadata-key", "description"],
)
def test_any_other_change_stays_a_group_wide_update(current, desired):
    """A real change of the shared group keeps the group-wide handling."""
    result, _ = _reconcile(current, desired)

    assert result["updated"] == [GROUP]
    assert not result["inventory_updated"]


def test_unreadable_host_map_stays_a_group_wide_update():
    """A map that is not a JSON mapping cannot be diffed per host."""
    result, _ = _reconcile(_spec("not json"), _spec(_mounts("node1")))

    assert result["updated"] == [GROUP]
    assert not result["inventory_updated"]


def test_identical_group_is_unchanged():
    """No difference means no update at all."""
    result, metadata = _reconcile(
        _spec(_mounts("node1", "node2")), _spec(_mounts("node1", "node2"))
    )

    assert result["unchanged"] == [GROUP]
    assert not result["updated"]
    assert not result["inventory_updated"]
    assert result["changed"] is False
    assert not metadata.updates


def test_new_group_is_created_not_an_inventory_update():
    """A group that does not exist yet is created."""
    metadata = FakeMetadata({})
    reconciler = object.__new__(OpenChamiReconciler)
    reconciler.metadata = metadata

    result = reconciler.reconcile_metadata_groups(
        [{"metadata": {"name": GROUP}, "spec": _spec(_mounts("node1"))}], PROJECT
    )

    assert result["created"] == [GROUP]
    assert not result["inventory_updated"]


def _hosts_template(*entries, before="runcmd: [a]\n", after="runcmd: [b]\n"):
    """Return group template text whose /etc/hosts block lists ``entries``."""
    lines = "".join(f"            {ip} {name}\n" for name, ip in entries)
    return (
        before
        + "          content: |\n"
        + "            # omnia-inventory-begin\n"
        + lines
        + "            # omnia-inventory-end\n"
        + after
    )


def _hosts_spec(*entries, **kwargs):
    return _spec(None, template=_hosts_template(*entries, **kwargs))


def test_a_new_hosts_line_concerns_only_the_new_host():
    """Adding a node to the /etc/hosts block names that node and nothing else."""
    result, metadata = _reconcile(
        _hosts_spec(("n1", "10.0.0.1"), ("n2", "10.0.0.2")),
        _hosts_spec(("n1", "10.0.0.1"), ("n2", "10.0.0.2"), ("n3", "10.0.0.3")),
    )

    assert result["inventory_updated"] == {GROUP: ["n3"]}
    assert not result["updated"]
    assert metadata.updates == [GROUP], "the group must still be written"


def test_a_changed_address_concerns_only_that_host():
    """Only the host whose line changed is named."""
    result, _ = _reconcile(
        _hosts_spec(("n1", "10.0.0.1"), ("n2", "10.0.0.2")),
        _hosts_spec(("n1", "10.0.0.1"), ("n2", "10.0.0.9")),
    )

    assert result["inventory_updated"] == {GROUP: ["n2"]}
    assert not result["updated"]


def test_a_removed_hosts_line_names_no_host():
    """A removed node leaves nothing to reprovision."""
    result, _ = _reconcile(
        _hosts_spec(("n1", "10.0.0.1"), ("n2", "10.0.0.2")),
        _hosts_spec(("n1", "10.0.0.1")),
    )

    assert result["inventory_updated"] == {GROUP: []}
    assert not result["updated"]


def test_a_change_outside_the_hosts_block_stays_group_wide():
    """Text outside the markers is real group content."""
    result, _ = _reconcile(
        _hosts_spec(("n1", "10.0.0.1")),
        _hosts_spec(("n1", "10.0.0.1"), ("n2", "10.0.0.2"), after="runcmd: [c]\n"),
    )

    assert result["updated"] == [GROUP]
    assert not result["inventory_updated"]


def test_first_time_the_markers_appear_stays_group_wide():
    """A group written before the markers existed is updated as a whole once."""
    old = _spec(None, template="runcmd: [a]\n            10.0.0.1 n1\nruncmd: [b]\n")
    result, _ = _reconcile(old, _hosts_spec(("n1", "10.0.0.1")))

    assert result["updated"] == [GROUP]
    assert not result["inventory_updated"]


def test_unchanged_hosts_block_is_not_an_update():
    """The same block means no write."""
    same = _hosts_spec(("n1", "10.0.0.1"))
    result, metadata = _reconcile(same, _hosts_spec(("n1", "10.0.0.1")))

    assert result["unchanged"] == [GROUP]
    assert not metadata.updates
