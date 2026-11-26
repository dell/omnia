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

"""TopoLVM install and Kafka StorageClass contracts (ER-ORCH-011 Story 4).

Covers FR-3.1 (install from the offline repository, only when a purpose: kafka
entry is declared), FR-3.2 (StorageClass properties, default unchanged) and the
template-level part of TC-NFT-004 (pinned artefacts, no inline secrets, mount
option injection). AC-001, AC-002 and AC-007 on a live cluster stay with the
FVT cases TC-FVT-012 and TC-FVT-013.

No playbook runs and no cluster is touched. The install script runs under bash
with ``helm`` and ``kubectl`` stubbed on ``PATH``. Task decisions are checked by
evaluating the Jinja expressions read from the task files themselves.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any

import jinja2
import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
ROLES = REPO_ROOT / "src" / "orchestrator" / "roles"
K8S_CONFIG = ROLES / "k8s_config"
TOPOLVM_TEMPLATES = K8S_CONFIG / "templates" / "topolvm"
INSTALL_SCRIPT = TOPOLVM_TEMPLATES / "install-topolvm.sh.j2"
STORAGECLASS = TOPOLVM_TEMPLATES / "omnia-kafka-local-sc.yaml.j2"
VALUES = TOPOLVM_TEMPLATES / "topolvm-values.yaml.j2"
INSTALL_TASKS = K8S_CONFIG / "tasks" / "install_topolvm.yml"
NFS_TASKS = K8S_CONFIG / "tasks" / "create_k8s_config_nfs.yml"
ROLE_VARS = K8S_CONFIG / "vars" / "main.yml"
FIRST_CONTROL_PLANE = (
    ROLES / "provision_common" / "templates" / "metadata_svc"
    / "ms-group-service_kube_control_plane_first_x86_64.yaml.j2"
)

SC_NAME = "omnia-kafka-local"
NAMESPACE = "topolvm-system"
CHART_PKG = "topolvm-17.3.0"
LABEL_KEY = "omnia.dell.com/kafka-storage"
DIGEST_REF = re.compile(r"^\d+\.\d+\.\d+@sha256:[0-9a-f]{64}$")

HELM_STUB = """#!/bin/bash
echo "helm $*" >> "$STUB_DIR/calls"
case "$1" in
  status)
    [ "$HELM_STATUS" = absent ] && exit 1
    echo "{\\"info\\": {\\"status\\": \\"$HELM_STATUS\\"}}" ;;
  upgrade) exit "${HELM_INSTALL_RC:-0}" ;;
esac
exit 0
"""

KUBECTL_STUB = """#!/bin/bash
echo "kubectl $*" >> "$STUB_DIR/calls"
case "$*" in
  *"--dry-run=client"*) echo "apiVersion: v1" ;;
  *"apply -f -"*) cat > /dev/null ;;
  *"get sc -o jsonpath="*) [ -n "$DEFAULT_SC" ] && echo "$DEFAULT_SC" ;;
esac
exit 0
"""


def _jinja() -> jinja2.Environment:
    """Strict Jinja environment with the two Ansible filters the sources use."""
    env = jinja2.Environment(undefined=jinja2.StrictUndefined, keep_trailing_newline=True)
    env.filters["to_json"] = json.dumps
    env.filters["regex_replace"] = lambda value, pattern, repl="": re.sub(pattern, repl, value)
    return env


JINJA = _jinja()


def _render(template: Path, **context: Any) -> str:
    return JINJA.from_string(template.read_text(encoding="utf-8")).render(**context)


def _expression(text: str):
    """Compile an Ansible value: a ``{{ ... }}`` string or a bare ``when`` expression."""
    source = text.strip()
    if source.startswith("{{") and source.endswith("}}"):
        source = source[2:-2]
    return JINJA.compile_expression(source.strip(), undefined_to_none=False)


def _tasks(path: Path) -> list[dict[str, Any]]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _task(tasks: list[dict[str, Any]], name: str) -> dict[str, Any]:
    matches = [task for task in tasks if task.get("name") == name]
    assert len(matches) == 1, f"task '{name}' not found exactly once"
    return matches[0]


def _role_vars() -> dict[str, Any]:
    return yaml.safe_load(ROLE_VARS.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# install-topolvm.sh under stubbed helm and kubectl
# ---------------------------------------------------------------------------

class ScriptRun:
    """A rendered install script, its stubs and its staged artefacts in tmp_path."""

    def __init__(self, root: Path):
        self.root = root
        self.stage = root / "stage"
        self.stubs = root / "stubs"
        self.stage.mkdir()
        self.stubs.mkdir()
        for name, body in (("helm", HELM_STUB), ("kubectl", KUBECTL_STUB)):
            stub = self.stubs / name
            stub.write_text(body, encoding="utf-8")
            stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
        for name in (f"{CHART_PKG}.tar.gz", "topolvm-values.yaml", "omnia-kafka-local-sc.yaml"):
            (self.stage / name).write_text("staged\n", encoding="utf-8")
        text = _render(
            INSTALL_SCRIPT,
            _stage_dir=str(self.stage), _ns=NAMESPACE, _chart_pkg=CHART_PKG, _sc_name=SC_NAME,
        )
        assert "LOG=/var/log/install-topolvm.log" in text
        self.log = root / "install.log"
        self.script = root / "install-topolvm.sh"
        self.script.write_text(text.replace("/var/log/install-topolvm.log", str(self.log)),
                               encoding="utf-8")

    def run(self, helm_status: str = "absent", default_sc: str = "nfs-client",
            helm_install_rc: int = 0) -> subprocess.CompletedProcess:
        """Run the script with the stub behaviour selected by the arguments."""
        env = {
            "PATH": f"{self.stubs}:{os.environ.get('PATH', '/usr/bin:/bin')}",
            "STUB_DIR": str(self.root),
            "HELM_STATUS": helm_status,
            "DEFAULT_SC": default_sc,
            "HELM_INSTALL_RC": str(helm_install_rc),
        }
        return subprocess.run(["bash", str(self.script)], env=env, capture_output=True,
                              text=True, timeout=60, check=False)

    @property
    def calls(self) -> list[str]:
        """Every helm and kubectl invocation, in order."""
        path = self.root / "calls"
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    def calls_starting(self, prefix: str) -> list[str]:
        """The recorded invocations that start with ``prefix``."""
        return [call for call in self.calls if call.startswith(prefix)]


@pytest.fixture(name="script")
def fixture_script(tmp_path: Path) -> ScriptRun:
    """A fresh rendered install script with stubs and staged artefacts."""
    return ScriptRun(tmp_path)


def test_orch_ut_458_fresh_install_does_not_wait_for_pods(script: ScriptRun):
    """ORCH_UT_458: a fresh install runs helm without --wait and creates the StorageClass.

    The script runs on the first control-plane node before any worker joins, so
    waiting on TopoLVM pods would time out and leave no StorageClass (FR-3.1).
    """
    result = script.run(helm_status="absent")
    assert result.returncode == 0, result.stdout + result.stderr
    installs = script.calls_starting("helm upgrade --install topolvm")
    assert len(installs) == 1
    assert f"{script.stage}/{CHART_PKG}.tar.gz" in installs[0]
    assert f"--namespace {NAMESPACE}" in installs[0]
    assert "--wait" not in installs[0]
    assert f"kubectl apply -f {script.stage}/omnia-kafka-local-sc.yaml" in script.calls
    assert not [call for call in script.calls if call.startswith("kubectl") and " wait " in call]


def test_orch_ut_459_deployed_release_is_not_reinstalled(script: ScriptRun):
    """ORCH_UT_459: a deployed release is kept and the StorageClass is still applied."""
    result = script.run(helm_status="deployed")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not script.calls_starting("helm upgrade")
    assert not script.calls_starting("helm uninstall")
    assert f"kubectl apply -f {script.stage}/omnia-kafka-local-sc.yaml" in script.calls


@pytest.mark.parametrize("status", ["pending-install", "failed"])
def test_orch_ut_460_partial_release_is_reinstalled(script: ScriptRun, status: str):
    """ORCH_UT_460: a pending or failed release is removed and installed again."""
    result = script.run(helm_status=status)
    assert result.returncode == 0, result.stdout + result.stderr
    calls = script.calls
    uninstall = calls.index(f"helm uninstall topolvm -n {NAMESPACE} --wait")
    install = next(i for i, call in enumerate(calls) if call.startswith("helm upgrade --install"))
    assert uninstall < install


def test_orch_ut_461_kafka_storageclass_as_default_fails(script: ScriptRun):
    """ORCH_UT_461: the script fails when the Kafka StorageClass is the default (FR-3.2)."""
    result = script.run(default_sc=SC_NAME)
    assert result.returncode == 1
    assert "violates FR-3.2" in result.stdout


def test_orch_ut_462_missing_chart_stops_before_install(script: ScriptRun):
    """ORCH_UT_462: a missing staged chart stops before helm and names Repo Manager (FR-3.1)."""
    (script.stage / f"{CHART_PKG}.tar.gz").unlink()
    result = script.run()
    assert result.returncode == 1
    assert "Chart tarball missing" in result.stdout and "Repo Manager" in result.stdout
    assert not script.calls_starting("helm upgrade")


def test_orch_ut_463_helm_failure_creates_no_storageclass(script: ScriptRun):
    """ORCH_UT_463: a failed helm install exits non-zero and applies no StorageClass."""
    result = script.run(helm_install_rc=1)
    assert result.returncode == 1
    assert "Helm install failed" in result.stdout
    assert not [call for call in script.calls if "omnia-kafka-local-sc.yaml" in call]


# ---------------------------------------------------------------------------
# StorageClass and Helm values manifests
# ---------------------------------------------------------------------------

def _storageclass(mount_options: list[str], volume_group: str = "vg-kafka-test") -> dict:
    return yaml.safe_load(
        _render(STORAGECLASS, _sc_name=SC_NAME, _vg=volume_group, _mount_opts=mount_options)
    )


def test_orch_ut_464_storageclass_has_every_fr_3_2_property():
    """ORCH_UT_464: the StorageClass carries every FR-3.2 property and is not default."""
    sc = _storageclass(["noatime", "nodiratime"])
    assert sc["kind"] == "StorageClass"
    assert sc["metadata"]["name"] == SC_NAME
    assert "annotations" not in sc["metadata"]
    assert sc["provisioner"] == "topolvm.io"
    assert sc["volumeBindingMode"] == "WaitForFirstConsumer"
    assert sc["reclaimPolicy"] == "Retain"
    assert sc["allowVolumeExpansion"] is True
    assert sc["parameters"] == {
        "csi.storage.k8s.io/fstype": "ext4",
        "topolvm.io/device-class": "vg-kafka-test",
    }
    assert sc["mountOptions"] == ["noatime", "nodiratime"]


def test_orch_ut_465_storageclass_without_mount_options():
    """ORCH_UT_465: no declared mount options means no mountOptions key."""
    assert "mountOptions" not in _storageclass([])


def test_orch_ut_466_mount_option_injection_stays_one_string():
    """ORCH_UT_466: a mount option with injected YAML stays one quoted value (TC-NFT-004)."""
    hostile = (
        'noatime"\nmetadata:\n'
        '  annotations: {storageclass.kubernetes.io/is-default-class: "true"}'
    )
    sc = _storageclass([hostile])
    assert sc["mountOptions"] == [hostile]
    assert "annotations" not in sc["metadata"]


def test_orch_ut_467_values_pin_image_and_select_kafka_nodes():
    """ORCH_UT_467: values pin the image digest from the role vars and target Kafka nodes."""
    role_vars = _role_vars()
    values = yaml.safe_load(_render(
        VALUES,
        _vg="vg-kafka-test",
        _img_ref=role_vars["topolvm_image_ref"],
        _label_key=role_vars["kafka_node_label_key"],
    ))
    assert role_vars["kafka_node_label_key"] == LABEL_KEY
    assert values["image"]["repository"] == "ghcr.io/topolvm/topolvm-with-sidecar"
    assert values["image"]["reference"] == role_vars["topolvm_image_ref"]
    assert DIGEST_REF.match(values["image"]["reference"])
    device_class = values["lvmd"]["deviceClasses"][0]
    assert device_class["name"] == device_class["volume-group"] == "vg-kafka-test"
    assert values["lvmd"]["nodeSelector"] == {LABEL_KEY: "true"}
    assert values["node"]["nodeSelector"] == {LABEL_KEY: "true"}
    assert values["cert-manager"]["enabled"] is False
    assert values["storageClasses"] == []


def test_orch_ut_468_artefacts_pinned_and_templates_hold_no_secrets():
    """ORCH_UT_468: chart and image are pinned; no TopoLVM template holds a secret (TC-NFT-004)."""
    role_vars = _role_vars()
    assert role_vars["topolvm_chart_package"] == CHART_PKG
    assert re.fullmatch(r"[0-9a-f]{64}", role_vars["topolvm_chart_sha256"])
    assert DIGEST_REF.match(role_vars["topolvm_image_ref"])
    secret_patterns = (
        re.compile(r"(?i)password\s*[:=]"),
        re.compile(r"(?i)\btoken\s*[:=]"),
        re.compile(r"-----BEGIN [A-Z ]*KEY-----"),
    )
    for template in sorted(TOPOLVM_TEMPLATES.glob("*.j2")):
        text = template.read_text(encoding="utf-8")
        for pattern in secret_patterns:
            assert not pattern.search(text), f"{template.name} matches {pattern.pattern}"


# ---------------------------------------------------------------------------
# install_topolvm.yml decisions, evaluated from the task file itself
# ---------------------------------------------------------------------------

def _vg_names(entries: list[dict[str, Any]]) -> list[str]:
    task = _task(_tasks(INSTALL_TASKS), "Resolve the declared Kafka volume group and mount options")
    return _expression(task["ansible.builtin.set_fact"]["_topolvm_vg_names"])(
        _kafka_disk_entries=entries)


def _single_vg_assertions(vg_names: list[str]) -> list[bool]:
    task = _task(_tasks(INSTALL_TASKS), "Validate a single declared Kafka volume group")
    return [bool(_expression(check)(_topolvm_vg_names=vg_names))
            for check in task["ansible.builtin.assert"]["that"]]


def test_orch_ut_469_single_declared_volume_group_is_enforced():
    """ORCH_UT_469: TopoLVM takes the declared VG and refuses two different VGs (FR-3.1)."""
    one = _vg_names([{"purpose": "kafka", "volume_group": "vg-a"},
                     {"purpose": "kafka", "volume_group": "vg-a"}])
    assert one == ["vg-a"]
    assert all(_single_vg_assertions(one))
    two = _vg_names([{"purpose": "kafka", "volume_group": "vg-a"},
                     {"purpose": "kafka", "volume_group": "vg-b"}])
    assert sorted(two) == ["vg-a", "vg-b"]
    assert not all(_single_vg_assertions(two))


@pytest.mark.parametrize(("declared", "expected"), [
    ("noatime,nodiratime", ["noatime", "nodiratime"]),
    (" noatime , nodiratime ,", ["noatime", "nodiratime"]),
    ("", []),
])
def test_orch_ut_470_declared_mount_options_become_a_list(declared: str, expected: list[str]):
    """ORCH_UT_470: the declared mount_options string becomes the StorageClass list (FR-3.2)."""
    task = _task(_tasks(INSTALL_TASKS), "Set TopoLVM device class and StorageClass mount options")
    expression = _expression(task["ansible.builtin.set_fact"]["_topolvm_mount_options"])
    entries = [{"purpose": "kafka", "volume_group": "vg-a", "mount_options": declared}]
    assert list(expression(_kafka_disk_entries=entries)) == expected


@pytest.mark.parametrize(("download", "expected_msg"), [
    ({"status_code": 404}, "topolvm_missing_artefact_msg"),
    ({"status_code": 503}, "topolvm_download_failed_msg"),
    ({"msg": "The checksum for ... did not match"}, "topolvm_download_failed_msg"),
])
def test_orch_ut_471_download_failure_names_the_real_cause(download: dict, expected_msg: str):
    """ORCH_UT_471: only HTTP 404 reports a missing artefact; other failures keep their error."""
    block = _task(_tasks(INSTALL_TASKS), "Download TopoLVM Helm chart from offline repository")
    fired = [task["ansible.builtin.fail"]["msg"] for task in block["rescue"]
             if _expression(task["when"])(topolvm_chart_download=download)]
    assert len(fired) == 1
    assert expected_msg in fired[0]
    messages = _role_vars()
    assert "Repo Manager" in messages["topolvm_missing_artefact_msg"]
    assert "topolvm_chart_download.msg" in messages["topolvm_download_failed_msg"]


@pytest.mark.parametrize("base", [
    "https://oim:2225/pulp/content/offline_repo/cluster/x86_64/rhel/10.0/tarball/",
    "https://oim:2225/pulp/content/offline_repo/cluster/x86_64/rhel/10.0/tarball",
])
def test_orch_ut_472_chart_url_follows_repo_manager_layout(base: str):
    """ORCH_UT_472: the chart URL is <tarball base>/<package>/<package>.tar.gz (FR-3.1)."""
    task = _task(_tasks(INSTALL_TASKS), "Resolve TopoLVM tarball URL from repo_status")
    value = task["ansible.builtin.set_fact"]["topolvm_chart_url"]
    url = JINJA.from_string(value).render(
        offline_tarball_path=base, topolvm_chart_package=CHART_PKG).strip()
    assert url == (
        "https://oim:2225/pulp/content/offline_repo/cluster/x86_64/rhel/10.0/tarball/"
        f"{CHART_PKG}/{CHART_PKG}.tar.gz"
    )


# ---------------------------------------------------------------------------
# AC-007: nothing is staged or installed without a purpose: kafka entry
# ---------------------------------------------------------------------------

def _first_node_topolvm_block() -> str:
    lines = FIRST_CONTROL_PLANE.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.startswith("{% if local_storage") and "kafka" in line)
    end = next(i for i in range(start, len(lines)) if lines[i].strip() == "{% endif %}")
    return "\n".join(lines[start:end + 1])


@pytest.mark.parametrize(("context", "installs"), [
    ({"local_storage": [{"purpose": "kafka", "volume_group": "vg-a"}]}, True),
    ({"local_storage": [{"purpose": "etcd"}]}, False),
    ({"local_storage": []}, False),
    ({}, False),
])
def test_orch_ut_473_first_node_installs_topolvm_only_for_kafka(context: dict, installs: bool):
    """ORCH_UT_473: first control-plane cloud-init runs the install only with a Kafka entry."""
    rendered = JINJA.from_string(_first_node_topolvm_block()).render(
        k8s_client_mount_path="/opt/omnia/k8s_mount", **context)
    assert ("/opt/omnia/k8s_mount/topolvm/install-topolvm.sh" in rendered) is installs


@pytest.mark.parametrize(("local_storage", "stages"), [
    ([{"purpose": "kafka", "volume_group": "vg-a"}, {"purpose": "etcd"}], True),
    ([{"purpose": "etcd"}], False),
    (None, False),
])
def test_orch_ut_474_artefacts_staged_only_for_kafka(local_storage, stages: bool):
    """ORCH_UT_474: Orchestrator stages TopoLVM artefacts only with a Kafka entry (AC-007)."""
    tasks = _tasks(NFS_TASKS)
    resolve = _task(tasks, "Resolve kafka disk entries from storage_config")
    include = _task(tasks, "Stage TopoLVM artefacts when a Kafka disk is declared")
    assert include["ansible.builtin.include_tasks"] == "install_topolvm.yml"
    context = {} if local_storage is None else {"local_storage": local_storage}
    entries = _expression(resolve["ansible.builtin.set_fact"]["_kafka_disk_entries"])(**context)
    assert bool(_expression(include["when"])(_kafka_disk_entries=entries)) is stages
