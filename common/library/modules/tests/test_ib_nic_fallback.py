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

"""Tests for InfiniBand NIC fallback detection (OMN01D-2442).

When iDRAC reports InfiniBand LinkStatus as 'Unknown', the IB NIC should
still be detected via the fallback path rather than silently skipped.
"""

import unittest
from unittest.mock import MagicMock


def _build_nic_info_list(ib_link_status="Unknown", ib_port_id="InfiniBand.Slot.7-1"):
    """Helper to build a nic_info_list fixture with controllable IB link status."""
    return [
        {
            "NicId": "NIC.Integrated.1",
            "Ports": [
                {
                    "PortId": "NIC.Integrated.1-1",
                    "LinkStatus": "Up",
                    "Partitions": [{"CurrentMacAddress": "AA:BB:CC:DD:EE:01"}],
                }
            ],
        },
        {
            "NicId": "InfiniBand.Slot.7",
            "Ports": [
                {
                    "PortId": ib_port_id,
                    "LinkStatus": ib_link_status,
                    "Partitions": [],
                }
            ],
        },
    ]


def _extract_ib_nic_name(nic_info_list):
    """Replicate the IB NIC extraction logic from extract_server_info.

    Priority: Up (best) > Unknown (fallback) > Down/other (last resort)
    """
    _IB_STATUS_PRIORITY = {"UP": 0, "UNKNOWN": 1}
    ib_nic_name = ""
    fallback_ib_nic_name = ""
    fallback_ib_priority = 99
    for nic in nic_info_list:
        nic_id = nic.get("NicId", "")
        if "infiniband" not in nic_id.lower():
            continue
        for port in nic.get("Ports", []):
            port_id = port.get("PortId", "")
            candidate = port_id if port_id else nic_id
            link_status = (port.get("LinkStatus") or "").strip().upper()
            if link_status == "UP":
                ib_nic_name = candidate
                break
            port_priority = _IB_STATUS_PRIORITY.get(link_status, 2)
            if port_priority < fallback_ib_priority:
                fallback_ib_nic_name = candidate
                fallback_ib_priority = port_priority
            elif port_priority == fallback_ib_priority and not fallback_ib_nic_name:
                fallback_ib_nic_name = candidate
        if ib_nic_name:
            break
    if not ib_nic_name and fallback_ib_nic_name:
        ib_nic_name = fallback_ib_nic_name
    return ib_nic_name


class TestIBNicFallback(unittest.TestCase):
    """OMN01D-2442: IB NIC detection when iDRAC reports Unknown LinkStatus."""

    def test_ib_nic_detected_when_link_up(self):
        """Normal case: IB NIC with LinkStatus 'Up' is detected."""
        nic_list = _build_nic_info_list(ib_link_status="Up")
        result = _extract_ib_nic_name(nic_list)
        self.assertEqual(result, "InfiniBand.Slot.7-1")

    def test_ib_nic_detected_when_link_unknown(self):
        """OMN01D-2442: IB NIC with LinkStatus 'Unknown' should still be detected via fallback."""
        nic_list = _build_nic_info_list(ib_link_status="Unknown")
        result = _extract_ib_nic_name(nic_list)
        self.assertEqual(result, "InfiniBand.Slot.7-1")

    def test_ib_nic_detected_when_link_empty(self):
        """IB NIC with empty LinkStatus should still be detected via fallback."""
        nic_list = _build_nic_info_list(ib_link_status="")
        result = _extract_ib_nic_name(nic_list)
        self.assertEqual(result, "InfiniBand.Slot.7-1")

    def test_ib_nic_detected_when_link_none(self):
        """IB NIC with None LinkStatus should still be detected via fallback."""
        nic_list = _build_nic_info_list(ib_link_status=None)
        result = _extract_ib_nic_name(nic_list)
        self.assertEqual(result, "InfiniBand.Slot.7-1")

    def test_ib_nic_detected_when_link_down(self):
        """IB NIC with LinkStatus 'Down' should still be detected via fallback."""
        nic_list = _build_nic_info_list(ib_link_status="Down")
        result = _extract_ib_nic_name(nic_list)
        self.assertEqual(result, "InfiniBand.Slot.7-1")

    def test_ib_nic_empty_when_no_ib_present(self):
        """No InfiniBand NIC in inventory should return empty string."""
        nic_list = [
            {
                "NicId": "NIC.Integrated.1",
                "Ports": [
                    {
                        "PortId": "NIC.Integrated.1-1",
                        "LinkStatus": "Up",
                        "Partitions": [{"CurrentMacAddress": "AA:BB:CC:DD:EE:01"}],
                    }
                ],
            }
        ]
        result = _extract_ib_nic_name(nic_list)
        self.assertEqual(result, "")

    def test_ib_nic_falls_back_to_nic_id_when_no_port_id(self):
        """When PortId is empty, NicId should be used as fallback."""
        nic_list = [
            {
                "NicId": "InfiniBand.Slot.7",
                "Ports": [
                    {
                        "PortId": "",
                        "LinkStatus": "Unknown",
                    }
                ],
            }
        ]
        result = _extract_ib_nic_name(nic_list)
        self.assertEqual(result, "InfiniBand.Slot.7")

    def test_prefers_link_up_over_unknown(self):
        """When multiple IB ports exist, prefer the one with LinkStatus 'Up'."""
        nic_list = [
            {
                "NicId": "InfiniBand.Slot.7",
                "Ports": [
                    {
                        "PortId": "InfiniBand.Slot.7-1",
                        "LinkStatus": "Unknown",
                    },
                    {
                        "PortId": "InfiniBand.Slot.7-2",
                        "LinkStatus": "Up",
                    },
                ],
            }
        ]
        result = _extract_ib_nic_name(nic_list)
        self.assertEqual(result, "InfiniBand.Slot.7-2")

    def test_prefers_unknown_over_down(self):
        """When no 'Up' port, prefer 'Unknown' over 'Down'."""
        nic_list = [
            {
                "NicId": "InfiniBand.Slot.7",
                "Ports": [
                    {
                        "PortId": "InfiniBand.Slot.7-1",
                        "LinkStatus": "Down",
                    },
                    {
                        "PortId": "InfiniBand.Slot.7-2",
                        "LinkStatus": "Unknown",
                    },
                ],
            }
        ]
        result = _extract_ib_nic_name(nic_list)
        self.assertEqual(result, "InfiniBand.Slot.7-2")

    def test_both_ports_down_picks_first(self):
        """When both ports are Down, pick the first one."""
        nic_list = [
            {
                "NicId": "InfiniBand.Slot.7",
                "Ports": [
                    {
                        "PortId": "InfiniBand.Slot.7-1",
                        "LinkStatus": "Down",
                    },
                    {
                        "PortId": "InfiniBand.Slot.7-2",
                        "LinkStatus": "Down",
                    },
                ],
            }
        ]
        result = _extract_ib_nic_name(nic_list)
        self.assertEqual(result, "InfiniBand.Slot.7-1")

    def test_both_ports_unknown_picks_first(self):
        """When both ports are Unknown, pick the first one."""
        nic_list = [
            {
                "NicId": "InfiniBand.Slot.7",
                "Ports": [
                    {
                        "PortId": "InfiniBand.Slot.7-1",
                        "LinkStatus": "Unknown",
                    },
                    {
                        "PortId": "InfiniBand.Slot.7-2",
                        "LinkStatus": "Unknown",
                    },
                ],
            }
        ]
        result = _extract_ib_nic_name(nic_list)
        self.assertEqual(result, "InfiniBand.Slot.7-1")

    def test_unknown_before_down_in_order(self):
        """Unknown port listed first, Down second — Unknown should be selected."""
        nic_list = [
            {
                "NicId": "InfiniBand.Slot.7",
                "Ports": [
                    {
                        "PortId": "InfiniBand.Slot.7-1",
                        "LinkStatus": "Unknown",
                    },
                    {
                        "PortId": "InfiniBand.Slot.7-2",
                        "LinkStatus": "Down",
                    },
                ],
            }
        ]
        result = _extract_ib_nic_name(nic_list)
        self.assertEqual(result, "InfiniBand.Slot.7-1")


if __name__ == "__main__":
    unittest.main()
