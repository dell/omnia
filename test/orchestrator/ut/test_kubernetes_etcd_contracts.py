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

"""Local-etcd boot-script, disk-media, recovery, and LDAP-gate contracts."""

import subprocess

import pytest
from library.functions import _workload_helpers as workload
from library.functions import kubernetes_recovery_pxeboot_func as recovery
from library.functions import kubernetes_runtime_pxeboot_func as runtime
from library.vars.pxeboot_vars import (
    ETCD_SETUP_LOG,
    ETCD_UPDATE_LOG,
    PXEBOOT_COMMANDS,
)

BOOT = 1_700_000_000


def test_boot_script_lines_are_parsed():
    """ORCH_UT_075: Boot-script state lines parse into mtime and DONE flags."""
    states = runtime._parse_boot_scripts(
        f"{ETCD_SETUP_LOG}|missing|0\n{ETCD_UPDATE_LOG}|{BOOT}|2\nnoise\n"
    )

    assert states[ETCD_SETUP_LOG] == (None, False)
    assert states[ETCD_UPDATE_LOG] == (BOOT, True)


@pytest.mark.parametrize(
    ("states", "expected"),
    [
        # First boot: the early fstab-update run fails, disk setup completes.
        (
            {ETCD_SETUP_LOG: (BOOT + 60, True), ETCD_UPDATE_LOG: (BOOT + 30, False)},
            ETCD_SETUP_LOG,
        ),
        # Later boot: setup log is gone, fstab-update completes.
        ({ETCD_SETUP_LOG: (None, False), ETCD_UPDATE_LOG: (BOOT + 30, True)}, ETCD_UPDATE_LOG),
        # A DONE marker left by an earlier boot is stale.
        ({ETCD_SETUP_LOG: (None, False), ETCD_UPDATE_LOG: (BOOT - 5, True)}, ""),
        # A current log without DONE means the script failed.
        ({ETCD_SETUP_LOG: (None, False), ETCD_UPDATE_LOG: (BOOT + 30, False)}, ""),
    ],
)
def test_completed_boot_script_requires_current_done(states, expected):
    """ORCH_UT_076: Only a DONE marker written on this boot counts."""
    assert runtime._completed_this_boot(states, BOOT) == expected


@pytest.mark.parametrize(
    ("disk", "media"),
    [
        ({"name": "nvme0n1", "tran": "nvme", "rota": False}, "nvme"),
        ({"name": "nvme1n1", "tran": None, "rota": "0"}, "nvme"),
        ({"name": "sdb", "tran": "sata", "rota": True}, "hdd"),
        ({"name": "sdb", "tran": "sas", "rota": "1"}, "hdd"),
        ({"name": "sdc", "tran": "sata", "rota": False}, "ssd"),
        ({"name": "sdc", "tran": "sata", "rota": None}, "unknown"),
    ],
)
def test_disk_media_classification(disk, media):
    """ORCH_UT_077: Disk media follows lsblk TRAN and ROTA like the 2.2 suite."""
    assert runtime._disk_media(disk) == media


def test_partition_resolves_to_parent_and_root_disk():
    """ORCH_UT_078: Partitions resolve to whole disks for root exclusion."""
    devices = runtime._flatten_devices(
        [
            {"name": "sda", "type": "disk", "children": [{"name": "sda2", "pkname": "sda"}]},
            {
                "name": "nvme0n1",
                "type": "disk",
                "pttype": "gpt",
                "children": [
                    {
                        "name": "nvme0n1p1",
                        "pkname": "nvme0n1",
                        "mountpoints": ["/var/lib/etcd"],
                    }
                ],
            },
        ]
    )
    by_name = {device["name"]: device for device in devices}
    selected = by_name["nvme0n1p1"]

    assert runtime._mountpoint_matches(selected, "/var/lib/etcd")
    assert runtime._parent_disk(selected, by_name)["name"] == "nvme0n1"
    assert runtime._root_disk_name("/dev/sda2", by_name) == "sda"


@pytest.mark.parametrize(
    ("states", "expected"),
    [
        ({ETCD_SETUP_LOG: (None, False), ETCD_UPDATE_LOG: (BOOT + 30, True)}, (True, True)),
        ({ETCD_SETUP_LOG: (BOOT + 40, True), ETCD_UPDATE_LOG: (BOOT + 30, True)}, (True, False)),
        ({ETCD_SETUP_LOG: (BOOT - 900, True), ETCD_UPDATE_LOG: (BOOT + 30, False)}, (False, True)),
    ],
)
def test_post_reboot_detects_disk_setup_rerun(monkeypatch, states, expected):
    """ORCH_UT_079: After reboot, fstab-update must finish and setup must not rerun."""
    monkeypatch.setattr(recovery, "etcd_boot_script_state", lambda _host, _row: (states, BOOT))

    assert recovery._post_reboot_boot_scripts(object(), {"HOSTNAME": "cp1"}) == expected


def _media_context(monkeypatch, expected, media_by_host):
    rows = [
        {
            "HOSTNAME": name,
            "ADMIN_IP": f"192.0.2.{index}",
            "EXPECTED_FUNCTIONAL_GROUP": "service_kube_control_plane_x86_64",
        }
        for index, name in enumerate(media_by_host, start=10)
    ]
    monkeypatch.setattr(runtime, "load_test_config", lambda: {"expected_etcd_disk_media": expected})
    monkeypatch.setattr(
        runtime, "_context", lambda _host: ({}, rows, rows[0], {"etcd_on_local_disk": True})
    )
    monkeypatch.setattr(
        runtime,
        "_etcd_disk_layout",
        lambda _host, row: ({}, media_by_host[row["HOSTNAME"]], {}, "sda"),
    )


def test_media_check_skips_when_not_configured(monkeypatch):
    """ORCH_UT_080: An empty expected media is a documented skip."""
    _media_context(monkeypatch, "", {"cp1": {"name": "sdb", "rota": "0"}})

    result = runtime.check_kubernetes_local_etcd_media(object())

    assert result["success"] and result["skipped"]


def test_media_check_rejects_unknown_media_value(monkeypatch):
    """ORCH_UT_081: An unsupported expected media fails closed."""
    _media_context(monkeypatch, "tape", {"cp1": {"name": "sdb", "rota": "0"}})

    result = runtime.check_kubernetes_local_etcd_media(object())

    assert not result["success"] and not result["skipped"]
    assert "expected_etcd_disk_media" in result["error"]


def test_media_check_requires_every_control_plane(monkeypatch):
    """ORCH_UT_082: One control plane on other media fails the check."""
    _media_context(
        monkeypatch,
        "nvme",
        {"cp1": {"name": "nvme0n1", "tran": "nvme"}, "cp2": {"name": "sdb", "rota": "0"}},
    )

    result = runtime.check_kubernetes_local_etcd_media(object())

    assert not result["success"]
    assert "cp2" in result["error"] and "cp1" not in result["error"]


@pytest.mark.parametrize(
    ("openldap", "validate", "reason"),
    [
        (False, True, "OpenLDAP is not enabled"),
        (True, False, "validate_external_ldap is false"),
        (True, True, ""),
    ],
)
def test_ldap_identity_checks_require_external_validation(monkeypatch, openldap, validate, reason):
    """ORCH_UT_083: LDAP-identity checks skip unless external LDAP is validated."""
    monkeypatch.setattr(
        workload, "load_external_ldap_settings", lambda: {"validation_enabled": validate}
    )

    result = workload.ldap_identity_skip({"features": {"openldap": openldap}})

    assert result.startswith(reason) if reason else result == ""


def test_boot_script_command_output_is_parseable(tmp_path):
    """ORCH_UT_084: The remote boot-script probe emits the parsed line format."""
    setup_log = tmp_path / "etcd-disk-setup.log"
    update_log = tmp_path / "diskless-etcd-mount.log"
    update_log.write_text("[INFO] start\n2026-01-01_00:00:00 [OK] ===== DONE =====\n")
    command = (
        PXEBOOT_COMMANDS["etcd_boot_scripts"]
        .replace(ETCD_SETUP_LOG, str(setup_log))
        .replace(ETCD_UPDATE_LOG, str(update_log))
    )

    output = subprocess.run(
        ["bash", "-c", command], capture_output=True, text=True, check=True, timeout=10
    ).stdout
    states = runtime._parse_boot_scripts(
        output.replace(str(setup_log), ETCD_SETUP_LOG).replace(str(update_log), ETCD_UPDATE_LOG)
    )

    assert states[ETCD_SETUP_LOG] == (None, False)
    assert states[ETCD_UPDATE_LOG][1] is True
    assert isinstance(states[ETCD_UPDATE_LOG][0], int)
