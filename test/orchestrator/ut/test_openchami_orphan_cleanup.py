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

"""Contracts for global SMD orphan cleanup when physical servers are replaced.

Reproduces the re-provision failure where a completely new set of physical
servers leaves stale XNAMEs in SMD groups, blocking
``prune_metadata_groups``.  ``cleanup_orphan_smd_entries`` must purge those
orphans so the later prune succeeds without a destructive full wipe.

The orphan test is keyed on SERVICE_TAG and MAC — never on a specific XNAME.
Every fixture here derives XNAMEs programmatically from an index so the tests
prove the behaviour holds for *any* allocation, not one magic value.
"""

# pylint: disable=wrong-import-position

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


# --- Generic identity generators (no hard-coded XNAMEs anywhere) -------------

def xname(index: int) -> str:
    """Derive a Node XNAME from an index, mirroring the SMD allocator."""
    return f"x1000c{index // 100}s{(index // 10) % 10}b{index % 10}n0"


def bmc_xname(node_xname: str) -> str:
    """Return the parent NodeBMC XNAME for a Node XNAME."""
    return node_xname[:-2]


def node_mac(index: int) -> str:
    """Return a unique normalized admin-NIC MAC for an index."""
    return f"{index:012x}"


def bmc_mac(index: int) -> str:
    """Return a unique normalized BMC-NIC MAC for an index."""
    return f"{index + 0x100000:012x}"


def service_tag(index: int) -> str:
    """Return a unique service tag for an index."""
    return f"SVCTAG{index:04X}"


def display_mac(normalized: str) -> str:
    """Render a normalized MAC with colons, as a PXE mapping would supply."""
    return ":".join(normalized[i:i + 2] for i in range(0, 12, 2))


class Node:
    """One physical server's full SMD footprint, derived from an index."""

    def __init__(self, index: int, group: str):
        self.index = index
        self.group = group
        self.xname = xname(index)
        self.bmc = bmc_xname(self.xname)
        self.tag = service_tag(index)
        self.node_mac = node_mac(index)
        self.bmc_mac = bmc_mac(index)

    def hardware(self) -> dict:
        return {
            "Type": "Node",
            "ID": self.xname,
            "PopulatedFRU": {"NodeFRUInfo": {"SerialNumber": self.tag}},
        }

    def ifaces(self) -> list:
        return [
            {
                "ID": self.node_mac,
                "MACAddress": self.node_mac,
                "ComponentID": self.xname,
                "Type": "Node",
            },
            {
                "ID": self.bmc_mac,
                "MACAddress": self.bmc_mac,
                "ComponentID": self.bmc,
                "Type": "NodeBMC",
            },
        ]


def build_state(nodes: list) -> tuple:
    """Assemble SMD hardware, interfaces, and groups for a set of nodes."""
    hardware = [n.hardware() for n in nodes]
    interfaces = [iface for n in nodes for iface in n.ifaces()]
    by_group: dict = {}
    for n in nodes:
        by_group.setdefault(n.group, []).append(n.xname)
    groups = [
        {"label": label, "members": {"ids": members}}
        for label, members in by_group.items()
    ]
    # A common group every node joins — exercises cross-group removal.
    groups.append(
        {"label": "ssh", "members": {"ids": [n.xname for n in nodes]}}
    )
    return hardware, interfaces, groups


def current_mapping(nodes: list) -> tuple:
    """Return the (service_tags, macs) a current PXE mapping would supply."""
    tags = [n.tag for n in nodes]
    macs = [display_mac(n.node_mac) for n in nodes] + [
        display_mac(n.bmc_mac) for n in nodes
    ]
    return tags, macs


class StatefulFakeSMD:
    """SMD double that *applies* deletes to its own state.

    Reading back after a delete reflects the mutation, which is what lets a
    second reconciler run observe a cleaned cluster and prove idempotency.
    """

    def __init__(self, hardware, interfaces, groups):
        self._hardware = [dict(r) for r in hardware]
        self._interfaces = [dict(r) for r in interfaces]
        self._groups = [
            {
                "label": g["label"],
                "members": {"ids": list(g.get("members", {}).get("ids", []))},
            }
            for g in groups
        ]
        self.calls = {
            "delete_group_member": 0,
            "delete_interfaces": 0,
            "delete_components": 0,
            "delete_hardware": 0,
        }
        self.removals = []

    # --- read surface (returns copies so callers cannot mutate state) ---
    def hardware_inventory(self):
        return [dict(r) for r in self._hardware]

    def interfaces(self):
        return [dict(r) for r in self._interfaces]

    def groups(self):
        return [
            {"label": g["label"], "members": {"ids": list(g["members"]["ids"])}}
            for g in self._groups
        ]

    # --- mutating surface ---
    @staticmethod
    def _clean(ids):
        return [str(v).strip() for v in ids if v]

    def delete_group_member(self, label, xname_arg):
        self.calls["delete_group_member"] += 1
        self.removals.append({"label": label, "xname": xname_arg})
        for group in self._groups:
            if group["label"] == label:
                group["members"]["ids"] = [
                    m for m in group["members"]["ids"] if m != xname_arg
                ]
        return True

    def delete_interfaces(self, interface_ids):
        ids = set(self._clean(interface_ids))
        self.calls["delete_interfaces"] += len(ids)
        self._interfaces = [
            r
            for r in self._interfaces
            if str(r.get("ID") or r.get("MACAddress")).strip() not in ids
        ]
        return {"deleted": sorted(ids), "missing": []}

    def delete_components(self, xnames):
        ids = self._clean(xnames)
        self.calls["delete_components"] += len(ids)
        return {"deleted": ids, "missing": []}

    def delete_component_endpoints(self, xnames):
        return {"deleted": self._clean(xnames), "missing": []}

    def delete_redfish_endpoints(self, xnames):
        return {"deleted": self._clean(xnames), "missing": []}

    def delete_hardware_inventory(self, xnames):
        ids = set(self._clean(xnames))
        self.calls["delete_hardware"] += len(ids)
        self._hardware = [
            r for r in self._hardware if str(r.get("ID")).strip() not in ids
        ]
        return {"deleted": sorted(ids), "missing": []}


def _reconciler(smd):
    """Build a reconciler bound to a fake SMD without a live client."""
    reconciler = object.__new__(OpenChamiReconciler)
    reconciler.smd = smd
    return reconciler


# --- Tests ------------------------------------------------------------------

@pytest.mark.parametrize(
    "old_indices, new_indices",
    [
        ([0, 3], [5, 6]),            # the reported login/compiler -> slurm swap
        ([10, 11, 12], [20, 21]),    # different blade range, different counts
        ([105, 250], [7]),           # crosses cabinet/slot boundaries
        ([1, 2, 3, 4], [50, 60]),    # many old -> few new
    ],
)
def test_orphans_purged_regardless_of_specific_xnames(old_indices, new_indices):
    """Any old server set is fully purged; detection is tag/MAC based."""
    old_nodes = [Node(i, f"old_group_{i}") for i in old_indices]
    new_nodes = [Node(i, f"new_group_{i}") for i in new_indices]
    hardware, interfaces, groups = build_state(old_nodes + new_nodes)
    tags, macs = current_mapping(new_nodes)
    smd = StatefulFakeSMD(hardware, interfaces, groups)

    result = _reconciler(smd).cleanup_orphan_smd_entries(
        current_service_tags=tags,
        current_macs=macs,
    )

    old_xnames = {n.xname for n in old_nodes}
    new_xnames = {n.xname for n in new_nodes}

    assert result["changed"] is True
    assert set(result["orphan_xnames"]) == old_xnames

    # Every old node is gone from every group; no new node is ever touched.
    touched = {r["xname"] for r in _group_removals(smd)}
    assert touched == old_xnames
    assert not (touched & new_xnames)

    # Hardware, interfaces, and components of the old nodes are purged;
    # the new nodes' footprint is untouched.
    assert {r["ID"] for r in smd.hardware_inventory()} == new_xnames
    surviving_components = {
        str(i["ComponentID"]) for i in smd.interfaces()
    }
    assert not (surviving_components & old_xnames)


def test_cleanup_is_idempotent_across_repeated_runs():
    """Running provision again after a replacement is a clean no-op.

    This is the task-5 guarantee: the second reconcile sees an already-clean
    cluster, reports ``changed: False`` and performs zero deletions.
    """
    old_nodes = [Node(i, f"old_group_{i}") for i in (0, 3)]
    new_nodes = [Node(i, f"new_group_{i}") for i in (5, 6, 7)]
    hardware, interfaces, groups = build_state(old_nodes + new_nodes)
    tags, macs = current_mapping(new_nodes)
    smd = StatefulFakeSMD(hardware, interfaces, groups)
    reconciler = _reconciler(smd)

    first = reconciler.cleanup_orphan_smd_entries(
        current_service_tags=tags, current_macs=macs
    )
    assert first["changed"] is True
    assert set(first["orphan_xnames"]) == {n.xname for n in old_nodes}

    calls_after_first = dict(smd.calls)

    # Second identical run against the now-cleaned state.
    second = reconciler.cleanup_orphan_smd_entries(
        current_service_tags=tags, current_macs=macs
    )
    assert second["changed"] is False
    assert second["orphan_xnames"] == []

    # No further mutations occurred on the second pass.
    assert smd.calls == calls_after_first

    # A third run stays a no-op too.
    third = reconciler.cleanup_orphan_smd_entries(
        current_service_tags=tags, current_macs=macs
    )
    assert third["changed"] is False
    assert smd.calls == calls_after_first


def test_fresh_install_with_empty_smd_is_a_noop():
    """First-ever provision (empty SMD) must not fail or report changes."""
    new_nodes = [Node(i, "slurm") for i in (5, 6)]
    tags, macs = current_mapping(new_nodes)
    smd = StatefulFakeSMD(hardware=[], interfaces=[], groups=[])

    result = _reconciler(smd).cleanup_orphan_smd_entries(
        current_service_tags=tags, current_macs=macs
    )

    assert result["changed"] is False
    assert result["orphan_xnames"] == []


def test_live_node_with_replaced_nic_is_not_orphaned():
    """A stale NIC MAC on a still-active service tag must not orphan a node."""
    live = Node(5, "slurm")
    stale_nic = {
        "ID": node_mac(999),
        "MACAddress": node_mac(999),
        "ComponentID": live.xname,
        "Type": "Node",
    }
    hardware, interfaces, groups = build_state([live])
    interfaces.append(stale_nic)  # old NIC still recorded against a live node
    tags, macs = current_mapping([live])
    smd = StatefulFakeSMD(hardware, interfaces, groups)

    result = _reconciler(smd).cleanup_orphan_smd_entries(
        current_service_tags=tags, current_macs=macs
    )

    assert result["changed"] is False
    assert result["orphan_xnames"] == []
    assert smd.calls["delete_group_member"] == 0


@pytest.mark.parametrize("active_interface_index", [0, 1])
def test_live_node_with_stale_service_tag_and_active_mac_is_not_orphaned(
    active_interface_index,
):
    live = Node(5, "slurm")
    hardware, interfaces, groups = build_state([live])
    hardware[0]["PopulatedFRU"]["NodeFRUInfo"]["SerialNumber"] = service_tag(999)
    smd = StatefulFakeSMD(hardware, interfaces, groups)

    result = _reconciler(smd).cleanup_orphan_smd_entries(
        current_service_tags=[live.tag],
        current_macs=[display_mac(interfaces[active_interface_index]["MACAddress"])],
        check_mode=True,
    )

    assert result["changed"] is False
    assert result["orphan_xnames"] == []
    assert smd.calls == {
        "delete_group_member": 0,
        "delete_interfaces": 0,
        "delete_components": 0,
        "delete_hardware": 0,
    }


def test_check_mode_reports_orphans_without_deleting():
    """Check mode plans the orphan purge but performs no mutations."""
    old_nodes = [Node(0, "login")]
    new_nodes = [Node(5, "slurm")]
    hardware, interfaces, groups = build_state(old_nodes + new_nodes)
    tags, macs = current_mapping(new_nodes)
    smd = StatefulFakeSMD(hardware, interfaces, groups)

    result = _reconciler(smd).cleanup_orphan_smd_entries(
        current_service_tags=tags,
        current_macs=macs,
        check_mode=True,
    )

    assert result["changed"] is True
    assert result["orphan_xnames"] == [old_nodes[0].xname]
    assert smd.calls == {
        "delete_group_member": 0,
        "delete_interfaces": 0,
        "delete_components": 0,
        "delete_hardware": 0,
    }


def test_component_only_orphan_without_hardware_record_is_cleaned():
    """A discovered node that never got a FRU record is still orphaned."""
    orphan = Node(0, "login")
    new_node = Node(5, "slurm")
    # Orphan has interfaces + group membership but no hardware inventory row.
    _, orphan_ifaces, _ = build_state([orphan])
    hardware = [new_node.hardware()]
    interfaces = orphan_ifaces + new_node.ifaces()
    groups = [
        {"label": orphan.group, "members": {"ids": [orphan.xname]}},
        {"label": new_node.group, "members": {"ids": [new_node.xname]}},
    ]
    tags, macs = current_mapping([new_node])
    smd = StatefulFakeSMD(hardware, interfaces, groups)

    result = _reconciler(smd).cleanup_orphan_smd_entries(
        current_service_tags=tags, current_macs=macs
    )

    assert result["changed"] is True
    assert result["orphan_xnames"] == [orphan.xname]
    assert {"label": orphan.group, "xname": orphan.xname} in _group_removals(smd)
    # Both the Node and its derived NodeBMC component are purged.
    assert smd.calls["delete_components"] == 2


def _group_removals(smd):
    """Return the group membership removals a run performed."""
    return smd.removals
