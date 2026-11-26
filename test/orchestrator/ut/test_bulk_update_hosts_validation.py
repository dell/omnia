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
"""Security tests for bulk_update_hosts input validation (OMN-SEC #1665)."""
# pylint: disable=protected-access

import importlib.util
from pathlib import Path
from unittest import mock

import pytest

_MODULE_PATH = (Path(__file__).resolve().parents[3] / "src" / "orchestrator"
                / "plugins" / "modules" / "bulk_update_hosts.py")
_spec = importlib.util.spec_from_file_location("bulk_update_hosts", _MODULE_PATH)
buh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(buh)

VALID_IPS = ["10.5.0.1", "192.168.1.255", "fd00::1", "2001:db8::10",
             "FD00:0:0::1", "fe80::1%eth0", "::ffff:10.0.0.1"]
VALID_NAMES = ["node001", "nid00001", "ctl-01", "ctl-01.cluster.local", "Node01"]
HOSTILE_NAMES = ["node1'; touch /tmp/x; echo '", "node1/e id/", "node1\n",
                 "node1\nOMNIA_HOSTS_EOF\ntouch /tmp/x", "node1;id", "$(id)",
                 "`id`", "node 1", "", "-node", "a" * 254, "node_01",
                 None, True, 12345]
HOSTILE_IPS = ["10.0.0.1; id", "10.0.0.1'", "10.0.0.1\n", "10.0.0.1/24",
               "999.1.1.1", " 10.0.0.1", "", None, 167772161,
               "fe80::1%a'b;id", "fe80::1%x\ntouch"]


@pytest.mark.parametrize("ip", VALID_IPS)
def test_valid_ips_accepted(ip):
    """IPv4/IPv6 addresses, including zone IDs, pass validation."""
    assert buh._validate_inputs([ip], {"node001": ip}, []) == []


@pytest.mark.parametrize("name", VALID_NAMES)
def test_valid_hostnames_accepted(name):
    """RFC-1123 hostnames and FQDNs pass validation in every field."""
    assert buh._validate_inputs([name], {name: "10.5.0.1"}, [name]) == []


@pytest.mark.parametrize("name", HOSTILE_NAMES)
def test_hostile_hostnames_rejected_everywhere(name):
    """Shell, sed, and heredoc metacharacters are rejected in every hostname field."""
    assert buh._validate_inputs([], {name: "10.5.0.1"}, [])
    assert buh._validate_inputs([], {}, [name])
    assert buh._validate_inputs([name], {}, [])


@pytest.mark.parametrize("ip", HOSTILE_IPS)
def test_hostile_ips_rejected(ip):
    """Malformed or metacharacter-bearing IP values are rejected."""
    assert buh._validate_inputs([], {"node001": ip}, [])


def test_script_unchanged_for_valid_input():
    """Valid input still produces the same hosts block and sed patterns."""
    ip_map = {"node002": "10.5.0.2", "node001": "fd00::1"}
    assert buh._build_hosts_block(ip_map) == (
        "# BEGIN OMNIA MANAGED HOSTS\nfd00::1 node001\n10.5.0.2 node002\n# END OMNIA MANAGED HOSTS")
    assert r"(10\.5\.0\.2|fd00::1)" in buh._build_cleanup_sed(ip_map, [])
    assert r"(node002|node001)" in buh._build_cleanup_sed(ip_map, [])


def test_module_fails_before_any_ssh():
    """Invalid input fails the module before any SSH subprocess is started."""
    params = {"hosts": ["10.5.0.1"], "ip_name_map": {"node1'; id; '": "10.5.0.1"},
              "ssh_key_path": "/k", "nodes_to_remove": [],
              "ssh_max_parallel": 20, "ssh_connect_timeout": 10}
    fake = mock.MagicMock(params=params, check_mode=False)
    fake.fail_json.side_effect = SystemExit(1)
    with mock.patch.object(buh, "AnsibleModule", return_value=fake), \
         mock.patch.object(buh.subprocess, "run") as run, pytest.raises(SystemExit):
        buh.run_module()
    fake.fail_json.assert_called_once()
    run.assert_not_called()
