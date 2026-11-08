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

"""Contract tests: slapd.conf changes reach an already-running omnia_auth.

``deploy_openldap`` used to skip entirely when the container was running, so
template changes (such as the CD-004 ``security`` directive) never reached
existing deployments. The running path now renders a candidate, compares it
with the file mounted in the container, validates it with ``slaptest``,
installs it, restarts the service, and restores the previous file on failure.
"""

from pathlib import Path

import yaml

ROLE = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "orchestrator"
    / "roles"
    / "deploy_openldap"
)
MAIN = ROLE / "tasks" / "main.yml"
RECONCILE = ROLE / "tasks" / "reconcile_slapd_conf.yml"
VARS = ROLE / "vars" / "main.yml"


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _walk(tasks):
    for task in tasks or []:
        yield task
        for key in ("block", "rescue", "always"):
            yield from _walk(task.get(key))


def _named(tasks, name):
    return next(task for task in _walk(tasks) if task.get("name") == name)


def _argv(task):
    return task["ansible.builtin.command"]["argv"]


def test_credentials_load_before_running_and_fresh_paths():
    """Credentials load before the redeploy and reconcile paths."""
    outer = _load(MAIN)[0]["block"]
    names = [task.get("name") for task in outer]
    load = names.index("Load OpenLDAP credentials")
    deploy = "Deploy OpenLDAP when container is not running or runs a different image"
    assert load < names.index(deploy)
    reconcile = _named(
        outer, "Reconcile slapd.conf when container is already running the desired image"
    )
    assert reconcile["ansible.builtin.include_tasks"] == "reconcile_slapd_conf.yml"
    assert load < names.index(reconcile["name"])
    assert reconcile["when"] == [
        "not (omnia_auth_needs_deploy | bool)",
        "not (omnia_auth_external_proxy | bool)",
    ]


def test_candidate_is_private_and_compared_with_mounted_file():
    """The candidate is private and compared with the mounted file."""
    tasks = _load(RECONCILE)
    assert _load(VARS)["slapd_reconcile_tmp_dir"] == "/dev/shm"
    render = _named(tasks, "Render candidate slapd.conf")
    assert render["no_log"] is True
    assert render["ansible.builtin.template"]["mode"] == "0600"
    running = _named(tasks, "Read slapd.conf checksum used by the running container")
    assert _argv(running)[-2:] == ["sha256sum", "/etc/openldap/slapd.conf"]
    apply = _named(tasks, "Apply updated slapd.conf")
    assert "_slapd_candidate_stat.stat.checksum" in apply["when"]
    assert "_slapd_running_sum" in apply["when"]


def test_validation_precedes_install_and_restart():
    """The candidate is validated before it is installed and applied."""
    apply = _named(_load(RECONCILE), "Apply updated slapd.conf")
    names = [task.get("name") for task in apply["block"]]
    validate = _named(apply["block"], "Check candidate slapd.conf syntax")
    assert _argv(validate)[3:6] == ["slaptest", "-u", "-f"]
    order = [
        "Validate candidate slapd.conf inside the running container",
        "Back up deployed slapd.conf",
        "Install updated slapd.conf",
        "Restart omnia_auth service with updated slapd.conf",
        "Wait for OpenLDAP to answer after restart",
    ]
    assert [names.index(name) for name in order] == sorted(names.index(name) for name in order)
    for name in ("Back up deployed slapd.conf", "Install updated slapd.conf"):
        assert _named(apply["block"], name)["no_log"] is True


def test_failure_restores_previous_file_and_cleans_up():
    """A failed restart restores the previous file and cleans up."""
    tasks = _load(RECONCILE)
    apply = _named(tasks, "Apply updated slapd.conf")
    rescue = [task.get("name") for task in apply["rescue"]]
    assert rescue == [
        "Restore previous slapd.conf",
        "Restart omnia_auth service with previous slapd.conf",
        "Report slapd.conf update failure",
    ]
    restore = _named(apply["rescue"], "Restore previous slapd.conf")
    assert "_slapd_install is defined" in restore["when"]
    assert restore["no_log"] is True
    cleanup = tasks[0]["always"][0]
    assert cleanup["ansible.builtin.file"]["state"] == "absent"
    assert "_slapd_candidate.path" in cleanup["loop"] and "_slapd_backup.path" in cleanup["loop"]
