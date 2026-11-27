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

"""local-disk-prep.sh contracts with stubbed disk, LVM, mount and API commands.

Covers ER-ORCH-011 TC-UT-002 (node-side disk selection), TC-UT-005 (fresh and
reboot preparation, label decision) and the node logic behind TC-FVT-030.
No real disk, mount, LVM or Kubernetes API is touched: every external command
is a stub on ``PATH`` that records its arguments.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_TEMPLATE = (
    REPO_ROOT / "src" / "orchestrator" / "roles" / "provision_common" / "templates"
    / "k8s-scripts" / "local-disk-prep.sh.j2"
)
NODE = "10.60.0.105"
NFS_DIR = "/mnt/nfs-node"
DESTRUCTIVE = ("wipefs", "sgdisk", "parted", "mkfs", "pvcreate", "vgcreate", "vgremove")
LABEL_KEY = "omnia.dell.com/kafka-storage"

# name|type|tran|rota|serial|wwn|model|rm|mountpoint|fstype|label
NVME_1 = ("/dev/nvme0n1", "disk", "nvme", "0", "SER-N1", "WWN-N1", "NVME MODEL", "0", "", "", "")
NVME_2 = ("/dev/nvme1n1", "disk", "nvme", "0", "SER-N2", "WWN-N2", "NVME MODEL", "0", "", "", "")
HDD = ("/dev/sdc", "disk", "sata", "1", "SER-H", "WWN-H", "HDD MODEL", "0", "", "", "")
BOSS = ("/dev/sdb", "disk", "sata", "1", "SER-B", "WWN-B", "DELLBOSS VD", "0", "", "", "")
SSD = ("/dev/sdd", "disk", "sata", "0", "SER-S", "WWN-S", "SSD MODEL", "0", "", "", "")

LSBLK_STUB = r"""#!/bin/bash
inv="$LDP_INV"
col() { awk -F'|' -v d="$1" -v c="$2" '$1==d {print $c}' "$inv"; }
case "$1" in
  -dpno) cut -d'|' -f1 "$inv" ;;
  -dno)
    case "$2" in TYPE) c=2;; TRAN) c=3;; ROTA) c=4;; SERIAL) c=5;; WWN) c=6;; MODEL) c=7;; RM) c=8;; *) c=0;; esac
    [ "$c" -gt 0 ] && col "$3" "$c" ;;
  -nrpo)
    case "$2" in
      MOUNTPOINTS) col "$3" 9 ;;
      FSTYPE,LABEL) f=$(col "$3" 10); l=$(col "$3" 11); [ -n "$f" ] && echo "$f $l" ;;
    esac ;;
  -no) [ "$2" = PKNAME ] && grep "^$3 " "$LDP_PK" | cut -d' ' -f2 ;;
esac
exit 0
"""

CURL_STUB = r"""#!/bin/bash
out=""; method=GET; body=""
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2;; -X) method="$2"; shift 2;; -d) body="$2"; shift 2;;
    -w|--max-time|--cacert|--cert|--key|-H) shift 2;; *) shift;;
  esac
done
echo "$method $body" >> "$LDP_DIR/api.log"
if [ -f "$LDP_DIR/apifail" ]; then echo down > "$out"; echo 503; exit 0; fi
if [ "$method" = PATCH ]; then
  jq --argjson p "$body" '.metadata.labels = ((.metadata.labels + $p.metadata.labels) | with_entries(select(.value != null)))' \
    "$LDP_DIR/node.json" > "$LDP_DIR/node.new" && mv "$LDP_DIR/node.new" "$LDP_DIR/node.json"
fi
cp "$LDP_DIR/node.json" "$out"; echo 200
"""

RECORDERS = (
    "wipefs", "sgdisk", "parted", "mkfs.ext4", "mkfs.xfs", "pvcreate", "vgcreate", "vgremove",
    "vgchange", "vgscan", "vgimportdevices", "chown", "chmod", "groupadd", "useradd",
)
NO_OPS = ("modprobe", "sleep", "udevadm", "findmnt", "lspci", "partprobe", "umount", "mkdir", "systemctl", "lvmconfig")


class Sandbox:
    """A scratch node: stubbed commands, inventory, map, status folder and rendered script."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.stubs = root / "stubs"
        self.status_dir = root / "status"
        self.map_file = root / "disk-map.approved.json"
        self.marker = root / "marker"
        self.fstab = root / "fstab"
        self.inventory = root / "inv.txt"
        self.pk_file = root / "pk.txt"
        for folder in (self.stubs, self.status_dir):
            folder.mkdir()
        for name in ("calls", "mounted", "pvvg", "etcdlabel", "fstab", "pk.txt", "inv.txt"):
            (root / name).touch()
        self.set_mounted([NFS_DIR])
        self._write_stubs()
        text = SCRIPT_TEMPLATE.read_text(encoding="utf-8")
        text = "".join(line for line in text.splitlines(keepends=True) if line.strip() not in ("{% raw %}", "{% endraw %}"))
        text = text.replace("/etc/fstab", str(self.fstab)).replace("/var/log/local-disk-prep.log", str(root / "script.log"))
        text = text.replace('[ -b "$PART" ]', '[ -n "$PART" ]')
        self.script = root / "script.sh"
        self.script.write_text(text, encoding="utf-8")

    def _write_stubs(self) -> None:
        def stub(name: str, body: str) -> None:
            path = self.stubs / name
            path.write_text("#!/bin/bash\n" + body, encoding="utf-8")
            path.chmod(0o755)

        (self.stubs / "lsblk").write_text(LSBLK_STUB, encoding="utf-8")
        (self.stubs / "curl").write_text(CURL_STUB, encoding="utf-8")
        for name in ("lsblk", "curl"):
            (self.stubs / name).chmod(0o755)
        for name in RECORDERS:
            stub(name, 'echo "$(basename "$0") $*" >> "$LDP_DIR/calls"\nexit 0\n')
        for name in NO_OPS:
            stub(name, "exit 0\n")
        stub("mount", 'echo "mount $*" >> "$LDP_DIR/calls"\necho "$1" >> "$LDP_DIR/mounted"\n')
        stub("mountpoint", 'grep -qx "${2:-$1}" "$LDP_DIR/mounted"\n')
        stub("vgs", 'grep -q "^vgcreate" "$LDP_DIR/calls"\n')
        stub("pvs", 'cat "$LDP_DIR/pvvg"\nexit 0\n')
        stub("blkid", 'cat "$LDP_DIR/etcdlabel"\nexit 0\n')

    def set_disks(self, *rows: tuple[str, ...]) -> None:
        self.inventory.write_text("".join("|".join(row) + "\n" for row in rows), encoding="utf-8")

    def set_mounted(self, paths: list[str]) -> None:
        (self.root / "mounted").write_text("".join(f"{path}\n" for path in paths), encoding="utf-8")

    def write_map(self, entry: str, purpose: str, disk_type: str, disk_id: str = "", node: str = NODE) -> None:
        row = {"node": node, "entry": entry, "purpose": purpose, "disk_id": disk_id,
               "disk_identity": "serial", "disk_type": disk_type, "model": None}
        self.map_file.write_text(json.dumps({"checksum": "x", "rows": [row]}), encoding="utf-8")

    def args(self, purpose: str, **override: str) -> list[str]:
        values: dict[str, str] = {
            "purpose": purpose, "node": NODE, "map_file": str(self.map_file),
            "status_dir": str(self.status_dir), "marker": str(self.marker), "nfs_dir": NFS_DIR,
        }
        if purpose == "kafka":
            values.update(entry="kafka_disk", disk_type="nvme", volume_group="omnia-kafka-vg")
        else:
            values.update(entry="etcd_disk", disk_type="boss", fs_type="ext4",
                          mount_point="/var/lib/etcd", mount_options="noatime")
        values.update(override)
        return [token for key, value in values.items() for token in (f"--{key.replace('_', '-')}", value)]

    def run(self, *args: str, reboot: bool = False) -> subprocess.CompletedProcess:
        if reboot:
            self.marker.touch()
        env = {"PATH": f"{self.stubs}:/usr/bin:/bin", "LDP_INV": str(self.inventory),
               "LDP_PK": str(self.pk_file), "LDP_DIR": str(self.root)}
        return subprocess.run(["bash", str(self.script), *args], capture_output=True, text=True,
                              env=env, timeout=60, check=False)

    def calls(self) -> list[str]:
        return (self.root / "calls").read_text(encoding="utf-8").splitlines()

    def destructive(self) -> list[str]:
        return [call for call in self.calls() if call.startswith(DESTRUCTIVE)]

    def status(self) -> dict[str, Any]:
        return json.loads((self.status_dir / f"status-{NODE}.json").read_text(encoding="utf-8"))


@pytest.fixture(name="node")
def _node(tmp_path: Path) -> Sandbox:
    """Return a sandbox node; skip when jq (a node-image dependency) is missing."""
    if shutil.which("jq") is None:
        pytest.skip("jq is required by local-disk-prep.sh")
    return Sandbox(tmp_path)


def _failed(node: Sandbox, result: subprocess.CompletedProcess, fragment: str) -> None:
    """Assert a refusal: exit 1, ERROR line, failed status naming the case, no destructive command."""
    assert result.returncode == 1, result.stdout
    assert f"ERROR node={NODE} entry=" in result.stdout
    assert fragment in node.status()["reason"], node.status()
    assert node.status()["result"] == "failed"
    assert node.destructive() == []


def test_kafka_fresh_selector_prepares_only_the_matching_disk(node):
    """ORCH_UT_410: A selector-only Kafka node prepares its one NVMe disk and no other."""
    node.set_disks(HDD, NVME_1)
    node.write_map("kafka_disk", "kafka", "nvme")

    result = node.run(*node.args("kafka"))

    assert result.returncode == 0, result.stdout
    assert "pvcreate -ff -y /dev/nvme0n1" in node.calls()
    assert "vgcreate omnia-kafka-vg /dev/nvme0n1" in node.calls()
    assert not any("/dev/sdc" in call for call in node.calls())
    assert node.status()["result"] == "ok"


def test_kafka_fresh_override_selects_the_named_serial(node):
    """ORCH_UT_411: node_overrides disk_id wins over the selector when several disks match."""
    node.set_disks(NVME_1, NVME_2)
    node.write_map("kafka_disk", "kafka", "nvme", disk_id="SER-N2")

    result = node.run(*node.args("kafka"))

    assert result.returncode == 0, result.stdout
    assert "vgcreate omnia-kafka-vg /dev/nvme1n1" in node.calls()
    assert not any("/dev/nvme0n1" in call for call in node.calls())


def test_case_c_several_matches_without_override_is_refused(node):
    """ORCH_UT_412: Two matching disks and no override fail with the case C message."""
    node.set_disks(NVME_1, NVME_2)
    node.write_map("kafka_disk", "kafka", "nvme")

    result = node.run(*node.args("kafka"))

    _failed(node, result, "2 disks match 'kafka_disk'")
    assert "/dev/nvme0n1 /dev/nvme1n1" in node.status()["reason"]
    assert "node_overrides" in node.status()["action"]


def test_case_g_override_of_another_type_is_refused(node):
    """ORCH_UT_413: An override naming an HDD for an NVMe entry fails with the case G message."""
    node.set_disks(NVME_1, HDD)
    node.write_map("kafka_disk", "kafka", "nvme", disk_id="SER-H")

    result = node.run(*node.args("kafka"))

    _failed(node, result, "is 'hdd', but 'kafka_disk' requires 'nvme'")


def test_case_h_override_not_found_on_fresh_install(node):
    """ORCH_UT_414: An override serial that is absent fails with the case H message."""
    node.set_disks(NVME_1)
    node.write_map("kafka_disk", "kafka", "nvme", disk_id="NO-SUCH")

    result = node.run(*node.args("kafka"))

    _failed(node, result, "no 'nvme' disk with serial 'NO-SUCH' found for 'kafka_disk'")


def test_case_h_no_disk_of_the_declared_type(node):
    """ORCH_UT_415: A selector with no matching disk type fails with the case H message."""
    node.set_disks(HDD)
    node.write_map("kafka_disk", "kafka", "nvme")

    result = node.run(*node.args("kafka"))

    _failed(node, result, "no 'nvme' disk found for 'kafka_disk'")


@pytest.mark.parametrize(
    "ignored",
    [
        ("/dev/loop0", "loop", "", "0", "", "", "", "0", "/run/rootfsbase", "squashfs", ""),
        ("/dev/sda", "disk", "usb", "1", "SER-U", "", "IDSDM", "0", "", "", ""),
        ("/dev/sde", "disk", "sata", "0", "SER-R", "", "REMOVABLE", "1", "", "", ""),
        ("/dev/ram0", "disk", "", "0", "SER-M", "", "RAM", "0", "", "", ""),
    ],
    ids=["loop-live-image", "usb-idsdm", "removable", "ram"],
)
def test_loop_usb_removable_and_ram_devices_are_never_candidates(node, ignored):
    """ORCH_UT_416: Live image, USB, removable and RAM devices are skipped, so the node fails with case H."""
    node.set_disks(ignored)
    node.write_map("kafka_disk", "kafka", "nvme")

    result = node.run(*node.args("kafka"))

    _failed(node, result, "no 'nvme' disk found")


def test_case_i_mounted_disk_is_refused(node):
    """ORCH_UT_417: A mounted candidate disk is refused with the case I message."""
    node.set_disks(NVME_1[:8] + ("/mnt/data", "", ""))
    node.write_map("kafka_disk", "kafka", "nvme")

    _failed(node, node.run(*node.args("kafka")), "is in use (mounted or has a signature)")


def test_case_i_foreign_signature_is_refused(node):
    """ORCH_UT_418: A disk carrying a foreign filesystem signature is refused with the case I message."""
    node.set_disks(NVME_1[:9] + ("ext4", "customer_data"))
    node.write_map("kafka_disk", "kafka", "nvme")

    _failed(node, node.run(*node.args("kafka")), "is in use (mounted or has a signature)")


def test_own_kafka_volume_group_does_not_block_a_retry(node):
    """ORCH_UT_419: A disk that only carries the Omnia Kafka volume group is prepared again."""
    node.set_disks(NVME_1[:9] + ("LVM2_member", ""))
    (node.root / "pvvg").write_text("omnia-kafka-vg\n", encoding="utf-8")
    node.write_map("kafka_disk", "kafka", "nvme")

    result = node.run(*node.args("kafka"))

    assert result.returncode == 0, result.stdout
    assert "vgcreate omnia-kafka-vg /dev/nvme0n1" in node.calls()


def test_case_j_disk_without_serial_is_refused(node):
    """ORCH_UT_420: A disk with no serial or WWN is refused with the case J message."""
    node.set_disks(("/dev/nvme0n1", "disk", "nvme", "0", "", "", "NVME MODEL", "0", "", "", ""))
    node.write_map("kafka_disk", "kafka", "nvme")

    _failed(node, node.run(*node.args("kafka")), "has no serial or WWN")


def test_case_l_missing_saved_disk_on_reboot_fails_closed(node):
    """ORCH_UT_421: With the marker present, a missing saved serial fails with the case L message."""
    node.set_disks(NVME_1)
    node.write_map("kafka_disk", "kafka", "nvme", disk_id="NO-SUCH")

    result = node.run(*node.args("kafka"), reboot=True)

    _failed(node, result, "disk with serial 'NO-SUCH' (kafka_disk) not found")


def test_kafka_reboot_only_activates_the_volume_group(node):
    """ORCH_UT_422: Reboot with the volume group present activates it and issues no destructive command."""
    node.set_disks(NVME_1)
    (node.root / "pvvg").write_text("omnia-kafka-vg\n", encoding="utf-8")
    node.write_map("kafka_disk", "kafka", "nvme")

    result = node.run(*node.args("kafka"), reboot=True)

    assert result.returncode == 0, result.stdout
    assert "vgchange -ay omnia-kafka-vg" in node.calls()
    assert node.destructive() == []
    assert node.status()["result"] == "ok"


@pytest.mark.parametrize("vg_on_disk", ["", "other-vg"], ids=["no-volume-group", "other-volume-group"])
def test_kafka_reboot_without_its_volume_group_fails_closed(node, vg_on_disk):
    """ORCH_UT_423: Marker present but the Kafka volume group missing fails the node unchanged."""
    node.set_disks(NVME_1)
    (node.root / "pvvg").write_text(vg_on_disk, encoding="utf-8")
    node.write_map("kafka_disk", "kafka", "nvme")

    result = node.run(*node.args("kafka"), reboot=True)

    _failed(node, result, "volume group 'omnia-kafka-vg' not found on /dev/nvme0n1")
    assert "clean the node's NFS data" in node.status()["action"]


def test_etcd_fresh_creates_a_labelled_filesystem_on_the_selected_disk(node):
    """ORCH_UT_424: Fresh etcd partitions the BOSS disk, formats it omnia_etcd, mounts it and sets ownership."""
    node.set_disks(NVME_1, BOSS)
    node.write_map("etcd_disk", "etcd", "boss")

    result = node.run(*node.args("etcd"))

    assert result.returncode == 0, result.stdout
    assert any(call.startswith("parted -s /dev/sdb mklabel gpt") for call in node.calls())
    assert "mkfs.ext4 -F -L omnia_etcd /dev/sdb1" in node.calls()
    assert not any("/dev/nvme0n1" in call for call in node.calls())
    assert "LABEL=omnia_etcd /var/lib/etcd ext4 noatime 0 2" in node.fstab.read_text(encoding="utf-8")
    assert "chown etcd:etcd /var/lib/etcd" in node.calls() and "chmod 700 /var/lib/etcd" in node.calls()
    assert node.status()["result"] == "ok"


def test_etcd_fresh_xfs_uses_mkfs_xfs(node):
    """ORCH_UT_425: The declared xfs filesystem type is created with mkfs.xfs."""
    node.set_disks(BOSS)
    node.write_map("etcd_disk", "etcd", "boss")

    result = node.run(*node.args("etcd", fs_type="xfs"))

    assert result.returncode == 0, result.stdout
    assert "mkfs.xfs -f -L omnia_etcd /dev/sdb1" in node.calls()
    assert "xfs" in node.fstab.read_text(encoding="utf-8")


def test_etcd_fresh_prepares_its_own_labelled_disk_again(node):
    """ORCH_UT_426: A disk that only carries the Omnia etcd filesystem is prepared again on retry."""
    node.set_disks(BOSS[:9] + ("ext4", "omnia_etcd"))
    node.write_map("etcd_disk", "etcd", "boss")

    assert node.run(*node.args("etcd")).returncode == 0
    assert "mkfs.ext4 -F -L omnia_etcd /dev/sdb1" in node.calls()


def test_etcd_fresh_refuses_a_foreign_filesystem(node):
    """ORCH_UT_427: An etcd disk with a foreign filesystem is refused and left unchanged."""
    node.set_disks(BOSS[:9] + ("ext4", "etcd_data"))
    node.write_map("etcd_disk", "etcd", "boss")

    _failed(node, node.run(*node.args("etcd")), "is in use (mounted or has a signature)")


def test_etcd_reboot_remounts_by_label_without_formatting(node):
    """ORCH_UT_428: Reboot remounts the omnia_etcd filesystem on the resolved disk and changes no disk."""
    node.set_disks(BOSS)
    (node.root / "etcdlabel").write_text("/dev/sdb1\n", encoding="utf-8")
    node.pk_file.write_text("/dev/sdb1 sdb\n", encoding="utf-8")
    node.write_map("etcd_disk", "etcd", "boss")

    result = node.run(*node.args("etcd"), reboot=True)

    assert result.returncode == 0, result.stdout
    assert "mount /var/lib/etcd" in node.calls()
    assert node.destructive() == []
    assert "LABEL=omnia_etcd /var/lib/etcd ext4 noatime 0 2" in node.fstab.read_text(encoding="utf-8")


def test_etcd_reboot_without_the_labelled_filesystem_fails_closed(node):
    """ORCH_UT_429: Marker present but no omnia_etcd filesystem fails the node and tells the operator what to do."""
    node.set_disks(BOSS)
    node.write_map("etcd_disk", "etcd", "boss")

    result = node.run(*node.args("etcd"), reboot=True)

    _failed(node, result, "no filesystem labelled 'omnia_etcd' found")
    assert "reprovision" in node.status()["action"]


def test_etcd_reboot_with_the_label_on_another_disk_fails_closed(node):
    """ORCH_UT_430: The omnia_etcd filesystem must sit on the resolved disk, not on another one."""
    node.set_disks(BOSS, NVME_1)
    (node.root / "etcdlabel").write_text("/dev/nvme0n1p1\n", encoding="utf-8")
    node.pk_file.write_text("/dev/nvme0n1p1 nvme0n1\n", encoding="utf-8")
    node.write_map("etcd_disk", "etcd", "boss")

    result = node.run(*node.args("etcd"), reboot=True)

    _failed(node, result, "is on /dev/nvme0n1p1, not on the declared disk /dev/sdb")


def test_nfs_not_mounted_fails_before_touching_a_disk(node):
    """ORCH_UT_431: An unconfirmed NFS mount fails the node and issues no destructive command."""
    node.set_disks(NVME_1)
    node.write_map("kafka_disk", "kafka", "nvme")
    node.set_mounted([])

    result = node.run(*node.args("kafka"))

    _failed(node, result, f"the NFS mount {NFS_DIR} could not be confirmed")


def test_node_missing_from_the_map_fails_by_name(node):
    """ORCH_UT_432: A node with no map row fails and the message names the node and the map path."""
    node.set_disks(NVME_1)
    node.write_map("kafka_disk", "kafka", "nvme", node="10.60.0.99")

    result = node.run(*node.args("kafka"))

    _failed(node, result, f"node {NODE} is missing from the approved disk map {node.map_file}")


def test_unreadable_or_invalid_map_fails_closed(node):
    """ORCH_UT_433: A missing map file and a non-JSON map both fail without changing a disk."""
    node.set_disks(NVME_1)

    _failed(node, node.run(*node.args("kafka")), "cannot be read")
    node.map_file.write_text("not json", encoding="utf-8")
    _failed(node, node.run(*node.args("kafka")), "is not valid JSON")


def test_row_for_another_purpose_fails_closed(node):
    """ORCH_UT_434: A row whose purpose differs from the requested purpose is refused."""
    node.set_disks(NVME_1)
    node.write_map("kafka_disk", "etcd", "nvme")

    _failed(node, node.run(*node.args("kafka")), "has purpose 'etcd', expected 'kafka'")


def test_later_successful_run_clears_the_failed_status(node):
    """ORCH_UT_435: A failed status stays failed until a later run succeeds and writes ok."""
    node.write_map("kafka_disk", "kafka", "nvme")
    node.set_disks(HDD)
    _failed(node, node.run(*node.args("kafka")), "no 'nvme' disk found")

    node.set_disks(NVME_1)

    assert node.run(*node.args("kafka")).returncode == 0
    assert node.status()["result"] == "ok"


@pytest.mark.parametrize(
    ("override", "fragment"),
    [
        ({"mount_options": "defaults,nofail"}, "nofail is not allowed for etcd"),
        ({"fs_type": "nfs"}, "invalid value 'nfs' for --fs-type"),
        ({"mount_point": "/var/lib/etcd;reboot"}, "invalid value"),
        ({"node": "$(touch /tmp/pwned)"}, "invalid value"),
    ],
    ids=["nofail", "fs-type", "mount-point-injection", "node-injection"],
)
def test_unsafe_arguments_are_rejected_before_any_action(node, override, fragment):
    """ORCH_UT_436: Arguments outside the allowlists exit 2 and no command touches a disk."""
    node.set_disks(BOSS)
    node.write_map("etcd_disk", "etcd", "boss")

    result = node.run(*node.args("etcd", **override))

    assert result.returncode == 2
    assert fragment in result.stdout
    assert node.calls() == []
    assert not Path("/tmp/pwned").exists()


class Cluster:
    """A stubbed Node object behind the curl stub, plus the kubeconfig the label step reads."""

    def __init__(self, node: Sandbox) -> None:
        self.node = node
        self.kubeconfig = node.root / "kubelet.conf"
        (node.root / "ca.crt").touch()
        (node.root / "client.pem").touch()
        self.kubeconfig.write_text(
            "clusters:\n- cluster:\n    certificate-authority: " + str(node.root / "ca.crt")
            + "\n    server: https://10.60.0.200:6443\nusers:\n- user:\n    client-certificate: "
            + str(node.root / "client.pem") + "\n    client-key: " + str(node.root / "client.pem") + "\n",
            encoding="utf-8",
        )
        self.set_labels({"kubernetes.io/hostname": NODE})

    def set_labels(self, labels: dict[str, str]) -> None:
        (self.node.root / "node.json").write_text(
            json.dumps({"metadata": {"name": NODE, "labels": labels}}), encoding="utf-8")
        (self.node.root / "api.log").write_text("", encoding="utf-8")

    def label(self) -> str:
        document = json.loads((self.node.root / "node.json").read_text(encoding="utf-8"))
        return document["metadata"]["labels"].get(LABEL_KEY, "absent")

    def api_calls(self) -> list[str]:
        return [line.split()[0] for line in (self.node.root / "api.log").read_text(encoding="utf-8").splitlines()]

    def status(self, result: str, purpose: str = "kafka") -> None:
        record = {"node": NODE, "entry": "kafka_disk", "purpose": purpose, "result": result,
                  "reason": "", "action": ""}
        (self.node.status_dir / f"status-{NODE}.json").write_text(json.dumps(record), encoding="utf-8")

    def run(self, **override: str) -> subprocess.CompletedProcess:
        values = {"purpose": "kafka", "entry": "kafka_disk", "node": NODE,
                  "status_dir": str(self.node.status_dir), "kubeconfig": str(self.kubeconfig),
                  "label_retries": "2", "label_interval": "0"}
        values.update(override)
        tokens = [t for key, value in values.items() for t in (f"--{key.replace('_', '-')}", value)]
        return self.node.run("--label-only", *tokens)


@pytest.fixture(name="cluster")
def _cluster(node: Sandbox) -> Cluster:
    return Cluster(node)


def test_label_is_added_when_the_status_is_ok(cluster):
    """ORCH_UT_437: A node with status ok for kafka and no marker sets its own label."""
    cluster.status("ok")

    assert cluster.run().returncode == 0
    assert cluster.label() == "true"
    assert cluster.api_calls() == ["GET", "PATCH"]


def test_label_step_is_idempotent(cluster):
    """ORCH_UT_438: An already correct label causes no API change."""
    cluster.status("ok")
    cluster.set_labels({LABEL_KEY: "true"})

    assert cluster.run().returncode == 0
    assert cluster.api_calls() == ["GET"]


def test_disable_marker_removes_the_label(cluster):
    """ORCH_UT_439: The operator marker removes the label even when the status is ok."""
    cluster.status("ok")
    cluster.set_labels({LABEL_KEY: "true"})
    (cluster.node.status_dir / f"kafka-label-disabled-{NODE}").touch()

    assert cluster.run().returncode == 0
    assert cluster.label() == "absent"


def test_removing_an_absent_label_is_a_success(cluster):
    """ORCH_UT_440: Removing a label that is already absent changes nothing and succeeds."""
    cluster.status("ok")
    (cluster.node.status_dir / f"kafka-label-disabled-{NODE}").touch()

    assert cluster.run().returncode == 0
    assert cluster.api_calls() == ["GET"]


@pytest.mark.parametrize(
    "state",
    ["failed", "etcd-purpose", "no-file"],
    ids=["status-failed", "status-for-etcd", "no-status-file"],
)
def test_label_is_removed_unless_the_node_reported_ok_for_kafka(cluster, state):
    """ORCH_UT_441: A failed status, another purpose or no status leaves the node without the label."""
    cluster.set_labels({LABEL_KEY: "true"})
    if state == "failed":
        cluster.status("failed")
    elif state == "etcd-purpose":
        cluster.status("ok", purpose="etcd")

    assert cluster.run().returncode == 0
    assert cluster.label() == "absent"


def test_api_down_while_adding_is_a_warning(cluster):
    """ORCH_UT_442: A label that cannot be set is a warning and the node still boots."""
    cluster.status("ok")
    (cluster.node.root / "apifail").touch()

    result = cluster.run()

    assert result.returncode == 0
    assert "[WARN]" in result.stdout
    assert cluster.label() == "absent"


def test_api_down_while_removing_is_an_error(cluster):
    """ORCH_UT_443: A label that cannot be removed after a disk failure is an error."""
    cluster.status("failed")
    cluster.set_labels({LABEL_KEY: "true"})
    (cluster.node.root / "apifail").touch()

    result = cluster.run()

    assert result.returncode == 1
    assert f"ERROR node={NODE} entry=kafka_disk purpose=kafka" in result.stdout
    assert cluster.label() == "true"


def test_label_step_applies_to_kafka_only(cluster):
    """ORCH_UT_444: The label step rejects the etcd purpose before any API call."""
    result = cluster.run(purpose="etcd", entry="etcd_disk")

    assert result.returncode == 2
    assert cluster.api_calls() == []


def _write_disabled_map(node: Sandbox, purpose: str = "kafka") -> None:
    entry = "kafka_disk" if purpose == "kafka" else "etcd_disk"
    row = {"node": NODE, "entry": entry, "purpose": purpose, "disk_id": "",
           "disk_identity": "serial", "disk_type": "nvme", "model": None, "enabled": False}
    node.map_file.write_text(json.dumps({"checksum": "x", "rows": [row]}), encoding="utf-8")


@pytest.mark.parametrize("reboot", [False, True], ids=["fresh", "reboot"])
def test_disabled_kafka_row_changes_no_disk_and_reports_disabled(node, reboot):
    """ORCH_UT_475: A row with enabled false exits 0, writes status disabled and runs no disk command."""
    node.set_disks(NVME_1)
    (node.root / "pvvg").write_text("omnia-kafka-vg\n", encoding="utf-8")
    _write_disabled_map(node)

    result = node.run(*node.args("kafka"), reboot=reboot)

    assert result.returncode == 0, result.stdout
    assert "DONE (disabled)" in result.stdout
    assert node.calls() == []
    assert node.status()["result"] == "disabled"
    assert "ERROR" not in result.stdout


def test_disabled_etcd_row_fails_closed(node):
    """ORCH_UT_476: A disabled row for etcd is refused; etcd must have its disk."""
    node.set_disks(BOSS)
    _write_disabled_map(node, purpose="etcd")

    _failed(node, node.run(*node.args("etcd")), "is disabled, which is allowed only for purpose kafka")


def test_enabled_true_row_is_prepared_normally(node):
    """ORCH_UT_477: A row with enabled true (or no enabled key) is prepared as before."""
    node.set_disks(NVME_1)
    row = {"node": NODE, "entry": "kafka_disk", "purpose": "kafka", "disk_id": "",
           "disk_identity": "serial", "disk_type": "nvme", "model": None, "enabled": True}
    node.map_file.write_text(json.dumps({"checksum": "x", "rows": [row]}), encoding="utf-8")

    result = node.run(*node.args("kafka"))

    assert result.returncode == 0, result.stdout
    assert "vgcreate omnia-kafka-vg /dev/nvme0n1" in node.calls()
    assert node.status()["result"] == "ok"


def test_label_is_removed_when_the_status_is_disabled(cluster):
    """ORCH_UT_478: A disabled node never carries the Kafka label."""
    cluster.set_labels({LABEL_KEY: "true"})
    cluster.status("disabled")

    assert cluster.run().returncode == 0
    assert cluster.label() == "absent"
